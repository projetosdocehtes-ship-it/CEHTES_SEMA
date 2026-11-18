import configparser
import contextlib
import logging
import os
from typing import TYPE_CHECKING, Any, Optional

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import (
    QuerySet,
    Value,
)
from django.forms import DateField

from apps.home.models import models_home as models
from apps.home.tipos import TipoClasseRegistro
from apps.home.utils.texto_livro02_service import (
    importar_ficha_do_fb_e_gravar_no_livro02,
)
from core.utils.firebird_utils import FbConnection
from core.utils.formatacoes import formatar_nome

if TYPE_CHECKING:
    from apps.home.models import Livro02

logger = logging.getLogger(__name__)


def gerar_beep() -> None:
    # import winsound

    # frequency = 2500  # Define a frequência do beep
    # duration = 1000  # Define a duração do beep em milissegundos
    # winsound.Beep(frequency, duration)
    pass


def get_ini():
    path_dir = os.path.split(os.path.abspath(__file__))[0]
    config = configparser.ConfigParser()
    config.read(path_dir + "/Conexao.ini", encoding="utf-8")

    # Configurações
    config_firebird = {
        "IP": config["DADOS"]["IP"],
        "BANCO": config["DADOS"]["BANCO"],
        "PORTA": int(config["DADOS"]["PORTA"]),
        "USUARIO": config["DADOS"]["USUARIO"],
        "SENHA": config["DADOS"]["SENHA"],
        "CHARSET": config["DADOS"]["CHARSET"],
        "SOLICITAR_L01": config["DADOS"]["SOLICITAR_L01"],
    }

    # Configurações do PostgreSQL
    config_postgres = {
        "host": config["DESTINO"]["host"],
        "database": config["DESTINO"]["database"],
        "user": config["DESTINO"]["user"],
        "password": config["DESTINO"]["password"],
    }

    return config_firebird, config_postgres


# GERAR AS TABELAS BASICAS PARA IMPORTACAO
def gerar_tabelas_base_postgresql() -> None:
    # get_pessoas_do_fb()

    # Gravar Tipos de models.Vinculo
    db = FbConnection()
    tipos_vinculos = get_tipos_vinculos_do_fb(db)
    criar_tipos_de_vinculos_importados_do_fb(tipos_vinculos)


# Formatar para Gravar a data corretamente
def formatar_data(data: str) -> str:
    if str(data) != "None":
        if str(data) != "":
            return str(data[8:10]) + "." + str(data[5:7]) + "." + str(data[0:4])
        else:
            return None
    else:
        return None


# Gerar todos os documentos
def get_tipos_vinculos_do_fb(db: FbConnection):
    # conn = firebird.get_conexao_firebird()
    # get_conexao_firebird()

    # Comando SQL a executar
    query = " SELECT CHAVE_TIPOS_VINCULOS, TIPOVINCULO FROM TIPOS_VINCULOS "

    # Execute the SELECT statement:
    tipos_vinculos = []

    # cur.execute(query)
    # resultados = cur.fetchall()
    # resultados = firebird.processar_resultados_e_converter_decimal_para_int(resultados)
    # resultados = processar_resultados_e_converter_decimal_para_int(resultados)

    db = FbConnection() if db is None else db
    resultados = db.execute_query(query)

    if resultados:
        for c in resultados:
            # print("Tipo vinculo: ", c)
            tipos_vinculos.append(c.copy())

        try:
            tipos_vinculos[0]
        except Exception:
            logger.exception("TIPOS_VINCULOS NAO ENCONTRADO")
            raise

            tipos_vinculos = None

    return tipos_vinculos


# Gerar todas as pessoas
def get_pessoas_do_fb(vinculos: list, db: FbConnection) -> list:
    logger.info(f"PESSOAS: Obtendo pessoas do FB para {len(vinculos)} vinculos")

    # Filtrando itens que não são None e convertendo para string
    lista_pessoas = {
        str(item["CHAVE_PESSOAS"])
        for item in vinculos
        if item["CHAVE_PESSOAS"] is not None
    }
    lista_ids = ",".join(lista_pessoas)  # Criando a string para a cláusula SQL IN

    query = f"""
            SELECT CHAVE_PESSOAS, CPF, NOME, NACIONALIDADE, PROFISSAO, DOCUMENTO, NOMEPAI, NOMEMAE,
                DATA_CADASTRO, CIDADE, UF, CHAVE_CONJUGE, SEXO, CEP, EMAIL, ENDERECO,
                DATA_NASCIMENTO, DATA_EXPEDICAO, NATURALIDADE, PESSOA_JURIDICA, DATA_ATUALIZACAO,
                TELEFONE, CHAVE_CATEGORIAS, CHAVE_TIPO_REGIME, CHAVE_DOCUMENTOS, TIPO_PESSOA,
                NUMEROCONTROLE, NOME_ORIGINAL, ORGAO_EMISSOR, STATUS, DATACASAMENTO, TIPOCASAMENTO
            FROM PESSOAS
            WHERE CHAVE_PESSOAS IN ({lista_ids})
            """

    resultado = db.execute_query(query)
    logger.info(
        f"PESSOAS: {len(resultado)} pessoas encontradas no FB para {len(vinculos)} vinculos",
    )
    return resultado if resultado else None


# Gerar todas as pessoas
def get_vinculos_do_fb(registro_id, db: FbConnection):
    # print("VINCULOS: Obtendo vinculos")
    query = (
        " SELECT CHAVE_VINCULOS, CHAVE_IMOVEIS, CHAVE_PESSOAS, CHAVE_CATEGORIAS, "
        "DATA_TRANSFERENCIA, TIPO_ATO, NUMERO_ATO, SITUACAO, CHAVE_TIPOS_VINCULOS, "
        "PORCENT_AREA, LIVRO, FICHA, CHAVE_CONJUGE, DATA_CADASTRO, CHAVE_FUNCIONARIOS, "
        "DATA_AQUISICAOESTRANGEIRO, DATA_LAVRATURA, PORCENT_AREA1, DATACASAMENTO, "
        "TIPOCASAMENTO "
        "FROM VINCULOS WHERE CHAVE_IMOVEIS = "
        + str(registro_id)
        + "ORDER BY NUMERO_ATO, CHAVE_VINCULOS "
    )

    db = FbConnection() if db is None else db
    resultado = db.execute_query(query)
    return resultado if resultado else None


def get_registro_no_fb(imovel_id, db: FbConnection):
    query = (
        "  SELECT NUMERO, TIPO, CARTORIO, CHAVE_IMOVEIS FROM IMOVEIS WHERE CHAVE_IMOVEIS = "
        + str(imovel_id)
    )

    db = FbConnection() if db is None else db
    resultados = db.execute_query(query)

    if resultados:
        for c in resultados:
            numero_registro = c[0]
            tipo_registro = c[1]
            cartorio_imovel = c[2]
            registro_anterior = c[3]

    return numero_registro, tipo_registro, cartorio_imovel, registro_anterior


# Gerar protocolo a ser importado
def get_registro_do_fb(
    numero_registro,
    tipo_registro,
    cartorio_registro,
    db: FbConnection,
):
    query = (
        " SELECT FIRST 1 CHAVE_IMOVEIS,    CLASSE,       DATA_ABERTURA,  ENCERRADO,"
        "      IMOVEL_ANTERIOR,  NUMERO,       TIPO,           TIPO_UNIDADE,      "
        "      CARTORIO,         MUNICIPIO,    NUMINTEIRO,                        "
        "      CEP,              DATA_CRIACAO, ULTIMO_LIVRO,   ULTIMO_FOLHA,      "
        "      AREACONSTRUIDA,                                                    "
        "      NUMERO_NIRF, NUMERO_CCIR, CADAMBRURAL_CAR, CERTPOLIGONAL_INCRA,    "
        "      AREACONSTRUIDA_RES, AREACONSTRUIDA_COM, MATRICULA_CNM              "
        f"      FROM IMOVEIS i WHERE i.NUMERO = '{numero_registro}'"
        f"        AND  TIPO = '{tipo_registro}'"
        f"        AND  CARTORIO = '{cartorio_registro}'"
    )

    # Execute the SELECT statement:
    db = FbConnection() if db is None else db
    imovel = db.execute_query(query)

    # NAO ENCONTROU IMOVEL
    if imovel:
        return imovel
    else:
        return None

    # try:
    #     # print(comando)
    #     # print(list_imovel)

    #     NUMERO_IMOVEL = int(list_imovel[0][0])
    #     # print("O imovel e ", NUMERO_IMOVEL)
    # except Exception as e:
    #     logger.exception("ERRO")
    #     # print("Imovel pesquisado: ", numero, tipo, cartorio)

    #     # print("IMOVEL NAO ENCONTRADO: ", str(numero))
    #     # logging.warning(f"IMOVEL NAO ENCONTRADO: = {str(numero)}")

    #     list_imovel = None

    # return list_imovel


# Gerar fic auxiliares a ser importado
def get_fichas_auxiliares_do_imovel_no_firebird(imovel_id, db: FbConnection):
    query = (
        " SELECT CHAVE_IMOVEIS, DATA_INCORPORACAO, NOME, NOME_INCORPORADORA, "
        # "        TIPO, NUMERO_EDIFICACAO, CONSTRUIDO, UNIDADE         "
        "        TIPO, NUMERO_EDIFICACAO, CONSTRUIDO, CHAVE_UNIDADES         "
        " FROM   FIC_AUXILIARES WHERE CHAVE_IMOVEIS =                        "
        + str(imovel_id)
    )

    # Execute the SELECT statement:
    # list_fic_auxiliares = []

    # try:
    db = FbConnection() if db is None else db
    return db.execute_query(query)

    #     if resultados:
    #         for c in resultados:
    #             list_fic_auxiliares.append(c)

    #         if len(list_fic_auxiliares) > 0:
    #             if list_fic_auxiliares[0][0] is None:
    #                 list_fic_auxiliares = []
    #             else:
    #                 int(list_fic_auxiliares[0][0])
    #         else:
    #             list_fic_auxiliares = []

    # except Exception:
    #     logger.exception(f"fic_auxiliares NAO ENCONTRADO: imovel_id: {imovel_id}")
    #     list_fic_auxiliares = []
    #     raise


# Gerar anteriores a ser importado
def get_registros_anteriores_relacionados_do_fb(registro_id, db: FbConnection):
    query = f"""
                SELECT CHAVE_IMOVEIS, NUMERO, TIPO, COMPLEMENTO
                FROM ANTERIORES
                WHERE CHAVE_IMOVEIS = {registro_id!s}
                """

    return db.execute_query(query)

    # try:
    #     if resultados:
    #         list_anteriores = [c["CHAVE_IMOVEIS"] for c in resultados]
    #         if len(list_anteriores) > 0:
    #             int(list_anteriores[0])
    #         else:
    #             return []
    #     else:
    #         return []

    # except Exception:
    #     logger.exception(f"anteriores NAO ENCONTRADO: imovel_id: {registro_id}")
    #     list_anteriores = []
    #     raise


# Gerar contribuinte a ser importado
def get_contribuintes_do_fb(imovel_id, db: FbConnection) -> None:
    query = (
        " SELECT CHAVE_IMOVEIS, CHAVE_CONTRIBUINTES, NUMERO_CONTRIBUINTE, VALOR "
        f" FROM CONTRIBUINTES WHERE CHAVE_IMOVEIS = {imovel_id}"
    )

    db = FbConnection() if db is None else db
    resultado = db.execute_query(query)

    if isinstance(resultado, dict):
        resultado = [resultado]  # Converte o dicionário em uma lista

    return resultado


# Gerar rurais a ser importado
def get_rurais_nomes_do_fb(imovel_id, db: FbConnection):
    # conn = firebird.get_conexao_firebird()
    # get_conexao_firebird()

    # Comando SQL a executar
    query = (
        " SELECT CHAVE_IMOVEIS, CHAVE_RURAIS_NOMES, NOME, LOCALIZACAO, AREA "
        " FROM   RURAIS_NOMES WHERE CHAVE_IMOVEIS = " + str(imovel_id)
    )

    # Execute the SELECT statement:
    list_rurais_nomes = []
    # cur.execute(comando)

    # resultados = cur.fetchall()
    # # resultados = firebird.processar_resultados_e_converter_decimal_para_int(resultados)
    # resultados = processar_resultados_e_converter_decimal_para_int(resultados)

    db = FbConnection() if db is None else db
    resultados = db.execute_query(query)

    if resultados:
        for resultado in resultados:
            c = list(resultado.values())
            list_rurais_nomes.append(c)

            print("area rural nomes:", c[2])

        try:
            rurais_id_nomes = int(list_rurais_nomes[0][0])
        except Exception:
            logger.exception(
                f"area rural nome NAO ENCONTRADO: CHAVE_RURAIS = {rurais_id_nomes!s} imovel: {imovel_id!s}",
            )
            raise

            list_rurais_nomes = None

    return list_rurais_nomes


# Gerar rurais a ser importado
def get_rurais_do_fb(imovel_id, db: FbConnection):
    # conn = firebird.get_conexao_firebird()
    # get_conexao_firebird()

    imovel_id = int(imovel_id)

    # Comando SQL a executar
    query = (
        " SELECT CHAVE_IMOVEIS, CHAVE_RURAIS, AREA, CARACTERISTICA, RESERVA_FLORESTAL, GEOREFERENCIAL, AREA_INTEIRO,  "
        "        GLEBA, DATATEXTO, GLEBA2, LOCALIZACAO, REMANESCENTE                                                  "
        "        FROM RURAIS WHERE CHAVE_IMOVEIS = " + str(imovel_id)
    )

    # # Execute the SELECT statement:
    # cur.execute(comando)

    # resultados = cur.fetchall()
    # # resultados = firebird.processar_resultados_e_converter_decimal_para_int(resultados)
    # resultados = processar_resultados_e_converter_decimal_para_int(resultados)

    db = FbConnection() if db is None else db
    return db.execute_query(query)

    # if resultados:
    #     for c in resultados:
    #         list_rurais.append(c)
    #         # print("area rural:", c[2])
    #     try:
    #         int(list_rurais[0][0])
    #     except Exception as e:
    #         logger.exception("Area rural nao encontrada:")
    #         raise

    #         list_rurais = None

    # return list_rurais


# Gerar RUAS a ser importado
def get_ruas_do_fb(unidade, db: FbConnection) -> list:
    # conn = firebird.get_conexao_firebird()
    # get_conexao_firebird()

    # Comando SQL a executar
    query = (
        " SELECT CHAVE_RUAS, CHAVE_UNIDADES, NOME, NUMERO_EDIFICACAO, CHAVE_LOGRADOUROS"
        "        FROM RUAS   WHERE CHAVE_UNIDADES = " + str(unidade)
    )

    return db.execute_query(query)


# Gerar LOTE a ser importado
def get_lotes_da_unidade_no_firebird(unidade_id, db: FbConnection):
    logger.info(f"LOTE: Iniciando importação de lotes da unidade: {unidade_id}")

    query = (
        " SELECT CHAVE_LOTES,    CHAVE_UNIDADES,    AREA,        QUADRA,    SETOR,  RESIDENCIAL,        "
        "        NUMERO_UNIDADE, NUMERO_EDIFICACAO, SUPERQUADRA, CONJUNTO,  BLOCO,  OUTRAS              "
        "        FROM LOTES   WHERE CHAVE_UNIDADES = " + str(unidade_id)
    )

    if db is None:
        db = FbConnection()
        resultados = db.execute_query(query)
        db.close()
    else:
        resultados = db.execute_query(query)

    if resultados:
        logger.info(
            f"LOTE: {len(resultados)} lotes encontrados para a unidade {unidade_id}",
        )

    return resultados if resultados else None


# Gerar UNIDADE a ser importado
def get_unidades_do_registro_no_fb(registro_id, db: FbConnection):
    print("UNIDADE: Iniciando importação de unidades")
    # conn = firebird.get_conexao_firebird()
    # db = get_conexao_firebird()

    # Comando SQL a executar
    query = (
        " SELECT CHAVE_IMOVEIS,  CHAVE_UNIDADES, IMOVEL_ANTERIOR, NOME_EDIFICIO,         "
        "        NUMERO_UNIDADE, TIPO,           CONSTRUIDA,      SEQUENCIAL,            "
        "        DATA_CADASTRO,  BLOCO,          GLEBA,           QUADRA, LOTEAUX, AREA  "
        "        FROM UNIDADES  "
        " WHERE CHAVE_IMOVEIS = " + str(registro_id)
    )

    # Execute the SELECT statement:
    db = db if db else FbConnection()  # Se não for passado a conexão, cria uma nova
    resultado = db.execute_query(query)

    return resultado[0] if resultado else None

    # resultados = cur.fetchall()
    # # resultados = firebird.processar_resultados_e_converter_decimal_para_int(resultados)
    # resultados = processar_resultados_e_converter_decimal_para_int(resultados)

    # if resultados:
    #     for c in resultados:
    #         list_unidades.append(c)

    #     try:
    #         int(list_unidades[0][1])
    #         # print("O imovel e ", CHAVE_UNIDADES)
    #     except Exception:
    #         logger.exception("ERRO")
    #         print("models.Unidade nao encontrada:")
    #         logging.warning(f"UNIDADE NAO ENCONTRADA: CHAVE_IMOVEIS = {imovel_id!s}")

    #         # gerar_beep()

    #         # import time

    #         list_unidades = None


def deletar_vinculos_atuais(vinculos_fb) -> None:
    print("VINCULOS: Deletando vinculos atuais ")
    models.Vinculo.objects.filter(
        id__in=[vinculo[0] for vinculo in vinculos_fb],
    ).delete()


# INICIAR TIPOS VINCULOS DE GRAVAR
def criar_tipos_de_vinculos_importados_do_fb(tipos_de_viculos_do_fb) -> None:
    objetos_vinculos = []

    for item in tipos_de_viculos_do_fb:
        try:
            pk = str(item[0])
            tipo = str(item[1])
        except Exception:
            pk = item.get("CHAVE_TIPOS_VINCULOS", 0)
            tipo = item.get("descricao", "")

        objetos_vinculos.append(models.TipoVinculo(id=pk, descricao=tipo))

    try:
        # models.TipoVinculo.objects.bulk_create(objetos_vinculos, ignore_conflicts=True)
        models.TipoVinculo.objects.bulk_create(objetos_vinculos)

        # print("inserido TIPOS VINCULOS : ", id)
        # logger.info(f"TIPOS VINCULOS: {len(objetos_vinculos)} inseridos : {id}")
    except IntegrityError:
        logger.exception("ERRO ao criar TIPOS VINCULOS")


# INICIAR PESSOAS DE GRAVAR
def criar_pessoas_do_fb(pessoas_do_fb: list) -> QuerySet:
    # Identificar os IDs e preparar dicionário de pessoas por ID
    ids_pessoas = [p["CHAVE_PESSOAS"] for p in pessoas_do_fb if p.get("CHAVE_PESSOAS")]
    pessoas_por_id = {
        p["CHAVE_PESSOAS"]: p for p in pessoas_do_fb if p.get("CHAVE_PESSOAS")
    }

    # Buscar objetos existentes
    objetos_existentes = models.Livro05.objects.filter(pk__in=ids_pessoas)
    existentes_por_id = {obj.pk: obj for obj in objetos_existentes}

    # Listas para bulk_create e bulk_update
    novos_objs = []
    objs_para_atualizar = []

    for id_pessoa, pessoa_fb in pessoas_por_id.items():
        nome_formatado = formatar_nome(pessoa_fb.get("NOME"))
        defaults = {
            "cpf": pessoa_fb.get("CPF", ""),
            "nome": nome_formatado,
            "nacionalidade": pessoa_fb.get("NACIONALIDADE", "brasileira"),
            "profissao": pessoa_fb.get("PROFISSAO", "[Não Consta]"),
            "documento": pessoa_fb.get("DOCUMENTO", "[Não Consta]"),
            "nome_pai": formatar_nome(pessoa_fb.get("NOMEPAI", "[Não Consta]")),
            "nome_mae": formatar_nome(pessoa_fb.get("NOMEMAE", "[Não Consta]")),
            # "criado_em": adicionar_fuso_horario_em_data(
            #     pessoa_fb.get(8] , )f pessoa_fb.get(8] , )lse settings.MINDATE
            # ),
            "cidade": formatar_nome(pessoa_fb.get("CIDADE", "[Não Consta]")),
            "uf": pessoa_fb.get("UF", ""),
            "conjuge": pessoa_fb.get("CHAVE_CONJUGE", None),
            "sexo": pessoa_fb.get("SEXO", "M"),
            "cep": pessoa_fb.get("CEP", ""),
            "email": pessoa_fb.get("EMAIL", "[Não Consta]"),
            "endereco": pessoa_fb.get("ENDERECO", "[Não Consta]"),
            "data_nascimento": pessoa_fb.get("DATA_NASCIMENTO", settings.MINDATE),
            "data_expedicao": pessoa_fb.get("DATA_EXPEDICAO", settings.MINDATE),
            "naturalidade": pessoa_fb.get("NATURALIDADE", "brasileira"),
            # "pessoa_fb_juridica": pessoa_fb_juridica,
            "data_atualizacao": pessoa_fb.get("DATA_ATUALIZACAO", settings.MINDATE),
            "telefone": pessoa_fb.get("TELEFONE", ""),
            "estado_civil_id": pessoa_fb.get("CHAVE_CATEGORIAS", 0),
            "tipo_regime": pessoa_fb.get("CHAVE_TIPO_REGIME", 0),
            "tipo_documento": pessoa_fb.get("CHAVE_DOCUMENTOS", 0),
            # "tipo_pessoa_fb": tipo_pessoa_fb,
            "numero_controle": pessoa_fb.get("NUMEROCONTROLE", 0),
            "nome_original": pessoa_fb.get("NOME_ORIGINAL", nome_formatado),
            "orgao_emissor": pessoa_fb.get("ORGAO_EMISSOR", "SSP"),
            # "situacao": pessoa_fb.get("STATUS", ""),
            "situacao": pessoa_fb.get("STATUS", ""),
            "data_casamento": pessoa_fb.get("DATACASAMENTO", settings.MINDATE),
            "tipo_casamento": pessoa_fb.get("TIPOCASAMENTO", "[Não Consta]"),
        }

        if id_pessoa in existentes_por_id:
            obj = existentes_por_id[id_pessoa]

            for key, value in defaults.items():
                setattr(obj, key, value)
            objs_para_atualizar.append(obj)
        else:
            novos_objs.append(models.Livro05(pk=id_pessoa, **defaults))

    # Usar bulk_create e bulk_update
    with transaction.atomic():
        if novos_objs:
            models.Livro05.objects.bulk_create(novos_objs)
            # logger.info(f"PESSOAS: {len(novos_objs)} criadas:{novos_objs}")
        if objs_para_atualizar:
            models.Livro05.objects.bulk_update(
                objs_para_atualizar,
                fields=list(defaults.keys()),
            )
            # print(
            #     f"PESSOAS: {len(objs_para_atualizar)} atualizadas: {objs_para_atualizar}",
            # )

    return models.Livro05.objects.filter(pk__in=ids_pessoas)


# ATUALIZAR APOS IMPORTAR
def correcoes_sistema_importacao() -> None:
    with contextlib.suppress(Exception):
        models.Livro02.objects.filter(registro_anterior=0).update(
            registro_anterior=None,
        )

    # APENAS MONTE CARMELO
    # with contextlib.suppress(Exception):
    #     models.Vinculo.objects.filter(estado_civil_id=13).update(
    #         estado_civil_id=0,
    #         tipo_regime_casamento_id=13,
    #     )

    with contextlib.suppress(Exception):
        models.Vinculo.objects.filter(transferido_em="0001-01-01").update(
            transferido_em=None,
        )

    # models.Vinculo.objects.filter(data_aquisicaoestrangeiro="0001-01-01").update(
    #    data_aquisicaoestrangeiro=None
    # )
    # models.Vinculo.objects.filter(data_lavratura="0001-01-01").update(data_lavratura=None)
    # models.Vinculo.objects.filter(data_casamento="0001-01-01").update(data_casamento=None)


# INICIAR vINCULOS DE GRAVAR
# def criar_vinculos_do_fb(vinculos_do_fb: list) -> QuerySet:
#     print("VINCULOS: Criando ")
#     ids_vinculos = []

#     for vinculo in vinculos_do_fb:
#         if not vinculo["CHAVE_VINCULOS"]:
#             continue

#         try:
#             obj, created = models.Vinculo.objects.update_or_create(
#                 pk=vinculo["CHAVE_VINCULOS"],
#                 defaults={
#                     "imovel_id": vinculo.get("CHAVE_IMOVEIS", 0),
#                     "pessoa_id": vinculo.get("CHAVE_PESSOAS", 0),
#                     "estado_civil_id": vinculo.get("CHAVE_CATEGORIAS", 0),
#                     "transferido_em": vinculo.get("DATA_TRANSFERENCIA", settings.MINDATE),
#                     "tipo_ato": vinculo.get("TIPO_ATO", ""),
#                     "numero_ato": vinculo.get("NUMERO_ATO", 0),
#                     "situacao": vinculo.get("SITUACAO", "F"),
#                     "tipo_vinculo_id": vinculo.get("CHAVE_TIPOS_VINCULOS", 0),
#                     "area_pecentual": vinculo.get("PORCENT_AREA", 0),
#                     "livro": vinculo.get("LIVRO", ""),
#                     "ficha": vinculo.get("FICHA", ""),
#                     "criado_em": vinculo.get("DATA_CADASTRO", settings.MINDATE),
#                     "colaborador": vinculo.get("CHAVE_FUNCIONARIOS", 0),
#                     "data_aquisicaoestrangeiro": vinculo.get("DATA_AQUISICAOESTRANGEIRO", settings.MINDATE),
#                     "data_lavratura": vinculo.get("DATA_LAVRATURA", settings.MINDATE),
#                     "area_pecentual1": vinculo.get("PORCENT_AREA1", 0),
#                     "data_casamento": vinculo.get("DATACASAMENTO", settings.MINDATE),
#                     "tipo_casamento": vinculo.get("TIPOCASAMENTO", ""),
#                 },
#             )
#             ids_vinculos.append(obj.pk)
#             if created:
#                 logger.info(f"VINCULOS: {obj.tipo_vinculo} {obj.pessoa}, ID: {obj.pk} criado.")
#             else:
#                 logger.info(f"VINCULOS: {obj.tipo_vinculo} {obj.pessoa}, {obj.imovel}, ID: {obj.pk} atualizado.")

#         except Exception:
#             logger.exception("ERRO ao criar vinculos")
#             continue
#     return models.Vinculo.objects.filter(pk__in=ids_vinculos)


def criar_vinculos_do_fb(vinculos_do_fb: list) -> QuerySet:
    # Extraindo IDs dos vínculos e criando um dicionário de vínculos por ID
    ids_vinculos = [
        v["CHAVE_VINCULOS"] for v in vinculos_do_fb if v.get("CHAVE_VINCULOS")
    ]
    vinculos_por_id = {
        v["CHAVE_VINCULOS"]: v for v in vinculos_do_fb if v.get("CHAVE_VINCULOS")
    }

    # Buscar objetos existentes
    vinculos_existentes = models.Vinculo.objects.filter(pk__in=ids_vinculos)
    existentes_por_id = {vinculo.pk: vinculo for vinculo in vinculos_existentes}

    # Verificar se os IDs de tipo de vínculo existem na tabela home_tipovinculo
    tipo_vinculo_ids = [
        v["CHAVE_TIPOS_VINCULOS"]
        for v in vinculos_do_fb
        if v.get("CHAVE_TIPOS_VINCULOS")
    ]
    set(
        models.TipoVinculo.objects.filter(pk__in=tipo_vinculo_ids).values_list(
            "pk",
            flat=True,
        ),
    )

    novos_vinculos = []
    vinculos_para_atualizar = []

    for id_vinculo, dados_vinculo in vinculos_por_id.items():
        tipo_vinculo_id = dados_vinculo.get("CHAVE_TIPOS_VINCULOS", 0)

        # Verificação de chave estrangeira
        # if tipo_vinculo_id not in tipos_vinculos_existentes:
        # continue  # Pula a iteração se o tipo de vínculo não existir
        # GRAVAR O VINCULO POIS NECESSITA DELE
        try:
            # gerar_tabelas_base_postgresql()
            pass
        except Exception:
            logger.exception("ERRO ao criar tipos vinculos")

        defaults = {
            "imovel_id": dados_vinculo.get("CHAVE_IMOVEIS", 0),
            "pessoa_id": dados_vinculo.get("CHAVE_PESSOAS", 0),
            "estado_civil_id": dados_vinculo.get("CHAVE_CATEGORIAS", 0),
            "transferido_em": dados_vinculo.get("DATA_TRANSFERENCIA", settings.MINDATE),
            "tipo_ato": dados_vinculo.get("TIPO_ATO", ""),
            "numero_ato": dados_vinculo.get("NUMERO_ATO", 0),
            "situacao": dados_vinculo.get("SITUACAO", "F"),
            "tipo_vinculo_id": tipo_vinculo_id,
            "area_pecentual": dados_vinculo.get("PORCENT_AREA", 0),
            "livro": dados_vinculo.get("LIVRO", ""),
            "ficha": dados_vinculo.get("FICHA", ""),
            "criado_em": dados_vinculo.get("DATA_CADASTRO", settings.MINDATE),
            "colaborador": dados_vinculo.get("CHAVE_FUNCIONARIOS", 0),
            "data_aquisicaoestrangeiro": dados_vinculo.get(
                "DATA_AQUISICAOESTRANGEIRO",
                settings.MINDATE,
            ),
            "data_lavratura": dados_vinculo.get("DATA_LAVRATURA", settings.MINDATE),
            "area_pecentual1": dados_vinculo.get("PORCENT_AREA1", 0),
            "data_casamento": dados_vinculo.get("DATACASAMENTO", settings.MINDATE),
            "tipo_casamento": dados_vinculo.get("TIPOCASAMENTO", ""),
        }

        if id_vinculo in existentes_por_id:
            vinculo = existentes_por_id[id_vinculo]
            for key, value in defaults.items():
                setattr(vinculo, key, value)
            vinculos_para_atualizar.append(vinculo)
        else:
            novos_vinculos.append(models.Vinculo(pk=id_vinculo, **defaults))

    # Executar operações em massa
    try:
        with transaction.atomic():
            if novos_vinculos:
                models.Vinculo.objects.bulk_create(novos_vinculos)
            if vinculos_para_atualizar:
                models.Vinculo.objects.bulk_update(
                    vinculos_para_atualizar,
                    fields=list(defaults.keys()),
                )
    except IntegrityError:
        # Aqui você pode adicionar tratamento de erro conforme necessário
        pass

    return models.Vinculo.objects.filter(pk__in=ids_vinculos)


def criar_registro(registro: dict[str, Any]) -> Optional["Livro02"]:
    """
    Cria e salva um novo registro do modelo Livro02 no banco de dados.

    :param registro: Dicionário contendo os dados do registro.
    :return: O objeto Livro02 criado ou None se houver erro.
    """
    # Obtenção do número baseado na lógica fornecida
    numero = "".join([char for char in registro.get("campo5", "") if char.isdigit()])
    numero = numero if not registro.get("campo10") else str(int(registro["campo10"]))

    # Dicionário para mapear chaves aos campos do modelo Livro02
    campo_map = {
        "pk": ("campo0", str),
        "classe": ("campo1", str),
        "data_abertura": ("campo2", lambda x: x or "1899-01-01"),
        "encerrado": ("campo3", lambda x: str(x) if x else "F"),
        "registro_anterior": ("campo4", lambda x: str(x) if x else "0"),
        "numero": ("campo5", lambda x: numero),
        "tipo": ("campo6", str),
        "tipo_unidade": ("campo7", str),
        "cartorio": ("campo8", lambda x: str(x) if x else "1"),
        "municipio": ("campo9", str),
        "cep": ("campo11", lambda x: "" if not x else str(x)),
        "criado_em": ("campo12", lambda x: x or "1899-01-01"),
        "ultimo_livro": ("campo13", str),
        "ultimo_folha": ("campo14", str),
        "area_construida": ("campo15", str),
        "numero_nirf": ("campo16", str),
        "numero_ccirr": ("campo17", str),
        "numero_car": ("campo18", str),
        "numero_incra": ("campo19", str),
        "area_construida_residencial": ("campo20", str),
        "area_construida_comercial": ("campo21", str),
        "cnm": ("campo22", str),
    }

    # Criação do objeto Livro02 utilizando uma compreensão de dicionário
    obj_registro = models.Livro02(
        **{
            campo: transformacao(registro.get(chave, ""))
            for campo, (chave, transformacao) in campo_map.items()
        },
    )

    # Tentativa de salvar o objeto com tratamento de exceção
    try:
        obj_registro.save()
        return obj_registro
    except IntegrityError as e:
        logger.exception(f"Erro ao criar registro: {e}")
        return None


# GRAVAR CONDOMINIO
def criar_condominio(registro_id, db: FbConnection) -> None:
    print("CONDOMINIO: Criando condominio ")
    unidades_do_fb = get_unidades_do_registro_no_fb(registro_id=registro_id, db=db)

    if unidades_do_fb:
        try:
            unidades_criadas = criar_unidades(unidades_do_fb)

            if unidades_criadas:
                print("Gravou condominio")
            else:
                print("Nao gravou condominio")

        except Exception:
            logger.exception("ERRO ao criar condominio")
            raise


# GRAVAR FICHA AUXILIAR
def criar_fichas_auxiliares_do_registro(registro_id: int, db: FbConnection) -> list:
    print("FICHA AUXILIAR: Criando fichas auxiliares ")

    # Obter fichas auxiliares do imovel
    fichas_auxiliares = get_fichas_auxiliares_do_imovel_no_firebird(
        registro_id,
        db=db,
    )

    if fichas_auxiliares:
        objetos_ficha_auxiliares = []

        for ficha_auxiliar_fb in fichas_auxiliares:
            ficha_auxiliar = list(
                ficha_auxiliar_fb.values(),
            )  # Converte o dicionário em uma lista para acessar as posições
            try:
                print(
                    f"FICHA AUXILIAR: Construindo objeto Ficha_Auxiliar com dados: ID: {str(ficha_auxiliar[0]).split('.')[0]}",
                )
                objetos_ficha_auxiliares.append(
                    models.FichaAuxiliar(
                        id=(
                            "0"
                            if str(ficha_auxiliar[0]) == "None"
                            else str(ficha_auxiliar[0])
                        ),
                        data_incorporacao=(
                            ficha_auxiliar[1] if ficha_auxiliar[1] else "1899-01-01"
                        ),
                        nome=str(ficha_auxiliar[2]) if ficha_auxiliar[2] else "",
                        nome_incorporadora=(
                            str(ficha_auxiliar[3]) if ficha_auxiliar[3] else ""
                        ),
                        tipo=str(ficha_auxiliar[4]) if ficha_auxiliar[4] else "",
                        numero_edificacao=(
                            str(ficha_auxiliar[5]) if ficha_auxiliar[5] else ""
                        ),
                        construido=str(ficha_auxiliar[6]) if ficha_auxiliar[6] else "",
                        unidade_id=(
                            "0"
                            if str(ficha_auxiliar[7]) == "None"
                            else str(ficha_auxiliar[7])
                        ),
                    ),
                )
            except Exception:
                logger.exception("ERRO")
                print(
                    f"FICHA AUXILIAR: Construindo objeto Ficha_Auxiliar com dados: ID: {ficha_auxiliar[0]!s}",
                )

                continue

        try:
            models.FichaAuxiliar.objects.bulk_create(objetos_ficha_auxiliares)
            print(
                f"FICHA AUXILIAR: {len(objetos_ficha_auxiliares)} fichas auxiliares inseridas .",
            )
            return objetos_ficha_auxiliares
        except IntegrityError:
            logger.exception("ERRO ao criar fichas auxiliares: ")

            return None
    return None


# GRAVAR ANTERIORES
def importar_registros_anteriores_vinculados_do_fb(
    registro_id,
    db: FbConnection,
) -> None:
    print("ANTERIOR: Obtendo registros anteriores")
    registros_anteriores = get_registros_anteriores_relacionados_do_fb(
        registro_id,
        db,
    )

    # # GRAVAR O REGISTRO ANTERIOR - REAL
    for registro_anterior in registros_anteriores:
        numero_registro = registro_anterior.get("NUMERO", "0")
        tipo_registro = registro_anterior.get("TIPO", "M")
        cartorio_registro = "1"

        registro_fb = get_registro_do_fb(
            numero_registro=numero_registro,
            tipo_registro=tipo_registro,
            cartorio_registro=cartorio_registro,
            db=db,
        )

        if registro_fb:
            registro = gravar_registro_importado_do_fb(registro_fb, db=db)
            print("ANTERIOR: Gravando o registro anterior: ", registro.numero_registro)


# GRAVAR ANTERIORES
def criar_registros_anteriores(registro_anterior_id: int, db: FbConnection) -> list:
    print("REGISTRO ANTERIOR: Criando registros anteriores ")
    objetos_anteriores = []

    try:
        anteriores_do_fb = get_registros_anteriores_relacionados_do_fb(
            registro_anterior_id,
            db=db,
        )
    except Exception:
        anteriores_do_fb = None

    if anteriores_do_fb:
        for anterior in anteriores_do_fb:
            print(
                "REGISTRO ANTERIOR: Construindo Registro models.Anterior com dados:",
            )

            # Garanta que 'imovel' é um BigInteger.
            registro_anterior_id = (
                int(registro_anterior_id) if registro_anterior_id else None
            )

            # Atualize ou crie o objeto models.Anterior.
            if registro_anterior_id:
                try:
                    anterior_obj, created = models.Anterior.objects.update_or_create(
                        imovel_id=registro_anterior_id,
                        numero=anterior.get("NUMERO", ""),
                        tipo=anterior.get("TIPO", ""),
                        defaults={
                            "numero": anterior.get("NUMERO", ""),
                            "tipo": anterior.get("TIPO", ""),
                            "complemento": anterior.get("COMPLEMENTO", ""),
                        },
                    )
                    objetos_anteriores.append(anterior_obj)

                except Exception:
                    logger.exception("ERRO ao criar registro anterior")
                    continue
            else:
                print("REGISTRO ANTERIOR: ID do registro não encontrado")

            # Agora você pode verificar se o registro foi criado ou atualizado:
            print(
                (
                    "REGISTRO ANTERIOR: criado"
                    if created
                    else "REGISTRO ANTERIOR atualizado"
                ),
            )
            print(anterior.get("NUMERO", ""))


# GRAVAR CONTRIBUINTE
def criar_contribuinte(registro_id, db: FbConnection) -> None:
    # print("CONTRIBUINTE: Criando contribuintes: ", registro_id)

    objetos_contribuintes = []

    contribuintes_do_fb = get_contribuintes_do_fb(registro_id, db)

    # print("CONTRIBUINTE: ", contribuintes_do_fb)

    if contribuintes_do_fb:
        for contribuinte in contribuintes_do_fb:
            try:
                objetos_contribuintes, created = (
                    models.Contribuintes.objects.update_or_create(
                        pk=contribuinte["CHAVE_CONTRIBUINTES"],
                        defaults={
                            "imovel_id": str(registro_id),
                            "numero_contribuinte": (
                                0
                                if not contribuinte["NUMERO_CONTRIBUINTE"]
                                else str(contribuinte["NUMERO_CONTRIBUINTE"])
                            ),
                            "valor": (
                                0
                                if str(contribuinte["VALOR"]) == "None"
                                else str(contribuinte["VALOR"])
                            ),
                        },
                    )
                )

                print("models.Contribuintes inseridos .")

            except IntegrityError:
                logger.exception("ERRO ao criar contribuintes: ")

                return None

    return objetos_contribuintes


# GRAVAR RURAL
def criar_registros_rurais(registro: "Livro02", db: FbConnection):
    print("RURAL: Criando rurais ")
    # atualizar_rurais()

    registros_rurais_fb = get_rurais_do_fb(registro.pk, db)

    rurais = []
    if registros_rurais_fb:
        for registro_rural in registros_rurais_fb:
            registro_rural_fb = list(
                registro_rural.values(),
            )  # converte o dict numa lista para acessar as posições
            print(
                f"RURAL: Construindo objeto models.Rural com dados: ID: {registro_rural_fb[1]!s}",
            )

        rural_id = registro_rural_fb[0] if registro_rural_fb[0] else 0

        try:
            with transaction.atomic():
                registro_rural, created = models.Rural.objects.update_or_create(
                    imovel_id=rural_id,
                    defaults={
                        "area": registro_rural_fb[2] if registro_rural_fb[2] else "",
                        "caracteristica": (
                            registro_rural_fb[3] if registro_rural_fb[3] else ""
                        ),
                        "reserva_florestal": (
                            registro_rural_fb[4] if registro_rural_fb[4] else "F"
                        ),
                        "georeferencial": (
                            registro_rural_fb[5] if registro_rural_fb[5] else "F"
                        ),
                        "imovel_id": rural_id,
                    },
                )
        except IntegrityError:
            print(
                f"Erro de integridade ao criar ou atualizar o objeto models.Rural com imovel_id={rural_id}. Tentando recuperar.",
            )
            registro_rural = models.Rural.objects.get(imovel_id=rural_id)

        print(
            "RURAL: models.Rural criado."
            if created
            else "RURAL: models.Rural atualizado .",
        )

        rurais.append(registro_rural)

    return rurais or None


def criar_nomes_rurais(registro_id: int, db: FbConnection):
    rurais_nomes = get_rurais_nomes_do_fb(registro_id, db)

    objetos_nomes_rurais = []
    if rurais_nomes:
        for nome_rural_fb in rurais_nomes:
            print(
                f"NOME RURAL: Construindo objeto Nome models.Rural com dados: ID: {nome_rural_fb[0]}",
            )

            rural_nome_id = nome_rural_fb[0]

            try:
                nome_rural, created = models.RuralNome.objects.update_or_create(
                    imovel_id=rural_nome_id,
                    id=nome_rural_fb[1] if nome_rural_fb[1] else 0,
                    defaults={
                        "id": nome_rural_fb[1] if nome_rural_fb[1] else 0,
                        "imovel_id": nome_rural_fb[0] if nome_rural_fb[0] else 0,
                        "nome": (
                            ""
                            if str(nome_rural_fb[2]) == "None"
                            else str(nome_rural_fb[2])
                        ),
                        "localizacao": (
                            ""
                            if str(nome_rural_fb[3]) == "None"
                            else str(nome_rural_fb[3])
                        ),
                        "area": (
                            ""
                            if str(nome_rural_fb[4]) == "None"
                            else str(nome_rural_fb[4])
                        ),
                    },
                )

                print(
                    (
                        f"NOME RURAL: {nome_rural} criado."
                        if created
                        else f"NOME RURAL: {nome_rural} atualizado."
                    ),
                )

            except Exception:
                logger.exception(
                    f"NOME RURAL: Erro ao criar nome rural com o ID: {nome_rural_fb[1]}",
                )
                continue

    return objetos_nomes_rurais or None


# GRAVAR IMOVEL DA UNIDADE
def criar_registro_da_unidade(
    registro_id,
    criar_registro,
    db: FbConnection,
) -> "Livro02":
    print(
        "Provisorio: Verificar se o registro anterior antes de gravar o proximo: ",
        registro_id,
    )

    criar_registro = criar_registro or False

    # Obtem do registro anterior
    query = """ SELECT NUMERO, TIPO, CARTORIO
                  FROM IMOVEIS
                  WHERE CHAVE_IMOVEIS = """ + str(
        registro_id,
    )

    db = FbConnection() if db is None else db
    registro_fb = db.execute_query(query)
    # FORCAR CRIAR O IMOVEL
    if criar_registro:
        registro_fb = None

    if not registro_fb:  # SE NAO EXISTIR O IMOVEL
        (numero_registro, tipo_registro, cartorio_registro, registro_id) = (
            get_registro_no_fb(registro_id, db)
        )

        registro_fb = get_registro_do_fb(
            numero_registro,
            tipo_registro,
            cartorio_registro,
            db,
        )

        registro = models.Livro02.objects.filter(pk=registro_id).first()

        if registro:  # SE O IMOVEL EXISTIR ATUALIZAR ELE
            try:
                registro.update(
                    registro_anterior_id=0 if not registro_id else str(registro_id),
                )
            except Exception:
                msg = "Erro ao atualizar imovel"
                logger.exception(msg)
                logger.exception(msg)
                raise

        else:  # SE O REGISTRO NAO EXISTIR CRIA ELE
            registro_novo = models.Livro02.objects.criar_registro_com_dados_do_fb(
                registro_fb=registro_fb,
            )

            if (
                not registro_novo
            ):  # IMPORTAR O REGISTRO ANTERIOR ANTES DE GRAVAR O PROXIMO
                return None

            importar_registros_anteriores_vinculados_do_fb(
                registro_id=registro_novo.pk,
                db=db,
            )

            # GRAVAR CONDOMINIO
            if registro_novo.classe == TipoClasseRegistro.CONDOMINIO:
                criar_condominio(registro_id=registro_novo.pk, db=db)

            # GRAVAR RURAL
            if registro_novo.classe == TipoClasseRegistro.RURAL:
                imoveis_rurais = criar_registros_rurais(registro=registro_novo)
                if imoveis_rurais:
                    criar_nomes_rurais(registro_id=registro_novo.pk, db=db)

            # GRAVAR LOTE
            if registro_novo.classe == TipoClasseRegistro.LOTE:
                criar_lotes(registro_id=registro_novo.pk, db=db)

            # GERAR CONTRIBUINTE
            criar_contribuinte(registro_id=registro_novo.pk, db=db)

            # GERAR ANTERIORES
            criar_registros_anteriores(registro_anterior_id=registro_novo.pk)

            # GERAR FICHA AUXILIAR
            criar_fichas_auxiliares_do_registro(registro_id=registro_novo.pk)

            # GERAR E ATUALIZAR PESSOA
            vinculos_fb = get_vinculos_do_fb(registro_id=registro_novo.pk, db=db)

            if vinculos_fb:
                pessoas_fb = get_pessoas_do_fb(vinculos=vinculos_fb, db=db)
                if pessoas_fb:
                    criar_pessoas_do_fb(pessoas_fb)

                deletar_vinculos_atuais(vinculos_fb)
                if criar_vinculos_do_fb(vinculos_fb):
                    # print("VINCULOS: Ajustando estado_civil do vinculo do imovel")

                    # print("Atualizando o estado_civil do vinculo do imovel para 0 quando for 13")
                    models.Vinculo.objects.filter(estado_civil=13).update(
                        estado_civil=0,
                        tipo_regime_casamento_id=1,
                    )

            print("Excluindo os atos que não possuem dias úteis")
            models.AtoPratica.objects.filter(dias_uteis=None).update(dias_uteis=1)

    return registro_novo


# GRAVAR UNIDADE
# tipo_origem_unidade="L"   lote
# tipo_origem_unidade="C"   Condominio
def criar_unidades(unidades_do_fb):
    print("UNIDADE: Criando unidades ")
    objetos_unidades = []

    # Garante que unidades_do_fb seja sempre uma lista
    if isinstance(unidades_do_fb, dict):
        unidades_do_fb = [unidades_do_fb]  # Converte o dicionário em uma lista

    for unidade in unidades_do_fb:
        # unidade_fb = str(unidade["CHAVE_IMOVEIS"])
        unidade_fb = str(unidade["CHAVE_UNIDADES"])

        logger.info(
            f"UNIDADE: Construindo objeto models.Unidade com dados: ID: {unidade_fb}",
        )

        imovel_id = 0 if not unidade["CHAVE_IMOVEIS"] else unidade["CHAVE_IMOVEIS"]

        # IMPORTACAO INCORRETA
        # unidade_anterior, created = models.Livro02.objects.get_or_create(pk=imovel_id)
        # if tipo_origem_unidade == "C":
        #     # IMPORTAR CONDOMINIO
        #     imovel_anterior_id = 0 if not unidade["CHAVE_IMOVEIS"] else unidade["CHAVE_IMOVEIS"]
        #     unidade_anterior, created = models.Livro02.objects.get_or_create(pk=imovel_anterior_id)
        # else:
        #     # IMPORTAR LOTES
        #     imovel_anterior_id = 0 if not unidade["IMOVEL_ANTERIOR"] else unidade["IMOVEL_ANTERIOR"]
        #     unidade_anterior, created = models.Livro02.objects.get_or_create(pk=imovel_anterior_id)

        unidade_anterior = (
            0 if not unidade["IMOVEL_ANTERIOR"] else unidade["IMOVEL_ANTERIOR"]
        )
        logger.info(f"IMOVEL UNIDADE: dados: ID: {imovel_id}")
        logger.info(f"IMOVEL ANTERIOR: dados: ID: {unidade_anterior}")

        # import time

        # time.sleep(5)

        try:
            unidade_criada, created = models.Unidade.objects.update_or_create(
                pk=unidade_fb,
                defaults={
                    "imovel_id": imovel_id,
                    # "registro_anterior_id": 0 if not unidade_anterior else unidade_anterior.pk,
                    "registro_anterior_id": models.Livro02.objects.get_or_create(
                        pk=unidade_anterior,
                    )[0].pk,
                    "nome_edificio": unidade.get("NOME_EDIFICIO", ""),
                    "numero_unidade": unidade.get("NUMERO_UNIDADE", ""),
                    "tipo_id": models.TipoUnidade.objects.get_or_create(
                        id=unidade["TIPO"],
                        defaults={"descricao": unidade["TIPO"]},
                    )[0].id
                    if unidade.get("TIPO")
                    else models.TipoUnidade.get_tipo_unidade_padrao().id,
                    "construida": unidade.get("CONSTRUIDA", "0"),
                    "sequencial": unidade.get("SEQUENCIAL", 0),
                    "criado_em": (
                        unidade.get("DATA_CADASTRO", settings.MINDATE)
                        if unidade.get("DATA_CADASTRO")
                        else settings.MINDATE
                    ),
                    "bloco": unidade.get("BLOCO", ""),
                    "gleba": unidade.get("GLEBA", ""),
                    "quadra": unidade.get("QUADRA", ""),
                    "lote_auxiliar": unidade.get("LOTEAUX", ""),
                    "area": unidade.get("AREA", ""),
                },
            )

            if created:
                logger.info(
                    f"UNIDADE: {unidade_criada.numero_unidade} unidades inseridas .",
                )
            else:
                print(
                    f"UNIDADE: {unidade_criada.numero_unidade} unidades atualizadas .",
                )

            objetos_unidades.append(unidade_criada)
        except IntegrityError:
            logger.exception("ERRO ao criar unidade:")
            raise

    return objetos_unidades


# GRAVAR LOTES
def criar_lotes(registro_id, db: FbConnection) -> None:
    print("LOTE: Criando lotes:", registro_id)
    unidades_fb = get_unidades_do_registro_no_fb(registro_id, db=db)

    if unidades_fb is None:
        return []

    for _x in unidades_fb:
        if unidades_fb:
            unidades = criar_unidades(unidades_fb)

        if not unidades:
            print("LOTE: Unidades não encontradas para o registro informado.")
            return None

        for unidade in unidades:
            print(
                "UNIDADE LIGADA AO LOTE: ",
                unidade.id,
            )

            lotes_do_fb = get_lotes_da_unidade_no_firebird(unidade.id, db=db)

            # print("LOTES: ", lotes_do_fb)

            if lotes_do_fb:
                for lote_fb in lotes_do_fb:
                    lote = list(lote_fb.values())

                    lote_criado, created = models.Lote.objects.update_or_create(
                        pk=str(lote[0]),
                        defaults={
                            "unidade_id": str(lote[1]),
                            "area": "" if str(lote[2]) == "None" else str(lote[2]),
                            "quadra": "" if str(lote[3]) == "None" else str(lote[3]),
                            "setor": "" if str(lote[4]) == "None" else str(lote[4]),
                            "residencial": (
                                "" if str(lote[5]) == "None" else str(lote[5])
                            ),
                            "numero_unidade": (
                                "" if str(lote[6]) == "None" else str(lote[6])
                            ),
                            "numero_edificacao": (
                                "" if str(lote[7]) == "None" else str(lote[7])
                            ),
                            "superquadra": (
                                "" if str(lote[8]) == "None" else str(lote[8])
                            ),
                            "conjunto": "" if str(lote[9]) == "None" else str(lote[9]),
                            "bloco": "" if str(lote[10]) == "None" else str(lote[10]),
                            "outras": "" if str(lote[11]) == "None" else str(lote[11]),
                        },
                    )

                    if created:
                        print("LOTE: lote inserido.")

            # Pegando as models.Rua
            ruas = get_ruas_do_fb(unidade.id, db=db)

            if ruas:
                for rua in ruas:
                    rua_id = rua["CHAVE_RUAS"]
                    nome = rua.get("NOME", "")
                    numero_edificacao = rua.get("NUMERO_EDIFICACAO", "")
                    logradouro_id = rua["CHAVE_LOGRADOUROS"]
                    logradouro_id_saec = rua.get("CHAVE_LOGRADOURO_SAEC", None)

                    # NAO INFORMOU O SAEC
                    if logradouro_id_saec is None:
                        logradouro_id_saec = 177

                        # EXISTE LOGRADOURO SEM SER NO SAEC
                        if logradouro_id is not None:
                            logradouro_id = int(logradouro_id)

                            if logradouro_id == 1:  # RUA
                                logradouro_id_saec = 250
                            elif logradouro_id == 2:  # Avenida
                                logradouro_id_saec = 26
                            elif logradouro_id == 3:  # Travessa
                                logradouro_id_saec = 273
                            elif logradouro_id == 4:  # Praça
                                logradouro_id_saec = 215
                            elif logradouro_id == 5:  # Rodovia
                                logradouro_id_saec = 247
                            elif logradouro_id == 6:  # Corredor
                                logradouro_id_saec = 85
                            elif logradouro_id == 7:  # Via
                                logradouro_id_saec = 294
                            elif logradouro_id == 8:  # Penetração
                                logradouro_id_saec = 177
                            elif logradouro_id == 9:  # Alameda
                                logradouro_id_saec = 10

                    # print("logradouro:", logradouro_id)
                    print("logradouro_id_saec", logradouro_id_saec)

                    try:
                        rua_criado, created = models.Rua.objects.update_or_create(
                            pk=rua_id,
                            defaults={
                                "unidade_id": unidade.id,
                                "nome": str(nome),
                                "numero_edificacao": str(numero_edificacao),
                                # "logradouro_id": logradouro_id,
                                "logradouro_id": models.TipoLogradouro.objects.get_or_create(
                                    pk=logradouro_id_saec,
                                    defaults={"descricao": str(logradouro_id_saec)},
                                )[0].pk,
                            },
                        )
                    except Exception:
                        logger.exception("ERRO ao criar rua")
                        raise

                    print("RUA: criadas")

    return None


#
# MIGRADO PARA models.Livro02.objects.excluir_por_id <<<<<<<<<<<<<
#
# # Excluir para atualizar os dados do livro 02
# def excluir_livro02(registro_id: int, db: FbConnection) -> None:
#     # conn = firebird.get_conexao_firebird()
#     # get_conexao_firebird()

#     # Obtem a models.Unidade com base no imovel
#     query = f"SELECT CHAVE_UNIDADES, IMOVEL_ANTERIOR FROM UNIDADES  WHERE CHAVE_IMOVEIS = {registro_id!s}"
#     # cur.execute(comando)
#     # unidade = cur.fetchone()
#     # unidade = firebird.processar_resultados_e_converter_decimal_para_int(unidade)
#     # unidade = processar_resultados_e_converter_decimal_para_int(unidade)
#     db = FbConnection() if db is None else db
#     unidade_fb = db.execute_query(query)
#     db.close()

#     if unidade_fb:
#         # EXCLCUIR AS PARTES DO ATO
#         query = " SELECT CHAVE_VINCULOS FROM VINCULOS WHERE CHAVE_IMOVEIS = " + str(registro_id)
#         # cur.execute(comando)
#         # vinculos_fb = cur.fetchone()
#         # vinculos_fb = firebird.processar_resultados_e_converter_decimal_para_int(vinculos_fb)
#         # vinculos_fb = processar_resultados_e_converter_decimal_para_int(vinculos_fb)
#         db = FbConnection() if db is None else db
#         vinculos_fb = db.execute_query(query)
#         db.close()
#         if vinculos_fb:
#             # ids_vinculos = "".[vinculo["CHAVE_VINCULOS"] for vinculo in vinculos_fb]
#             ids_vinculos = [int(vinculo["CHAVE_VINCULOS"]) for vinculo in vinculos_fb]
#             PedidoParteAto.objects.filter(vinculo_id__in=ids_vinculos).delete()

#     # RETIRAR DO REGISTRO ANTERIOR
#     lista = []
#     for item in models.Unidade.objects.filter(registro_anterior_id=registro_id):
#         models.FichaAuxiliar.objects.filter(unidade_id=item.id).delete()
#         lista.append(item.id)

#     # RETIRAR DO REGISTRO ANTERIOR
#     if lista:
#         for item in lista:
#             models.Rua.objects.filter(unidade_id=item).delete()
#             models.Lote.objects.filter(unidade_id=item).delete()
#             models.Unidade.objects.filter(id=item).delete()

#     models.FichaAuxiliar.objects.filter(id=registro_id).delete()

#     if unidade_fb:
#         models.Rua.objects.filter(unidade_id=unidade_fb[0]["CHAVE_UNIDADES"]).delete()
#         models.Lote.objects.filter(unidade_id=unidade_fb[0]["CHAVE_UNIDADES"]).delete()
#         models.Unidade.objects.filter(id=unidade_fb[0]["CHAVE_UNIDADES"]).delete()
#         models.FichaAuxiliar.objects.filter(unidade_id=unidade_fb[0]["CHAVE_UNIDADES"]).delete()

#     models.Contribuintes.objects.filter(imovel_id=registro_id).delete()
#     models.Anterior.objects.filter(imovel_id=registro_id).delete()
#     models.Unidade.objects.filter(imovel_id=registro_id).delete()
#     models.RuralNome.objects.filter(imovel_id=registro_id).delete()
#     models.Rural.objects.filter(imovel_id=registro_id).delete()
#     models.Vinculo.objects.filter(imovel_id=registro_id).delete()
#     models.Unidade.objects.filter(imovel_id=registro_id).delete()
#     models.Livro02.objects.filter(pk=registro_id).delete()
#     models.Unidade.objects.filter(imovel_id=registro_id).delete()


# FINALIZAR PROCESSOS DE GRAVAR
def gravar_registro_importado_do_fb(registros_fb, db: FbConnection) -> "Livro02":
    for registro_fb in registros_fb:
        numero_do_registro = models.Livro02.get_numero_do_registro_pelo_id(
            registro_fb["CHAVE_IMOVEIS"],
        )

        logger.info(
            f"REGISTRO: Gravando registro : {numero_do_registro!s}, ******************** ",
        )

        # Excluir para atualizar os dados do livro 02
        models.Livro02.objects.excluir_por_id(registro_fb["CHAVE_IMOVEIS"])

        print(
            "REGISTRO: Iniciar gravação do registro ID: ",
            registro_fb["CHAVE_IMOVEIS"],
        )
        registro = models.Livro02.objects.criar_registro_com_dados_do_fb(registro_fb)
        if registro:
            # GRAVAR CONDOMINIO
            if registro.classe == "C":
                criar_condominio(registro.pk, db)

            # GRAVAR RURAL
            if registro.classe == "R":
                imoveis_rurais = criar_registros_rurais(registro=registro, db=db)
                if imoveis_rurais:
                    criar_nomes_rurais(registro.pk, db=db)

            # GRAVAR LOTE
            if registro.classe == TipoClasseRegistro.LOTE:
                criar_lotes(registro.pk, db=db)

            # GERAR CONTRIBUINTE
            criar_contribuinte(registro.pk, db=db)

            # GERAR ANTERIORES
            criar_registros_anteriores(registro_anterior_id=registro.pk, db=db)

            # GERAR FICHA AUXILIAR
            criar_fichas_auxiliares_do_registro(registro.pk, db=db)

            # GERAR E ATUALIZAR PESSOA
            vinculos_fb = get_vinculos_do_fb(registro.pk, db=db)

            if vinculos_fb:
                pessoas_fb = get_pessoas_do_fb(vinculos_fb, db=db)
                if pessoas_fb:
                    criar_pessoas_do_fb(pessoas_fb)

                # deletar_vinculos_atuais(vinculos_fb)
                criar_vinculos_do_fb(vinculos_fb)

            # FAZER CORRECOES
            correcoes_sistema_importacao()

            logger.info(
                f"\n\n\n\nREGISTRO: Mudando de registro: {registro.numero}, ********************************** ",
            )
        return registro
    return None
    # return None


# Inicio do Programa para converter
def converter_livro02_do_fb(iten_do_pedido: dict, db: FbConnection) -> None:
    from apps.home.utils.texto_livro02_service import (
        importar_ficha_do_fb_e_gravar_no_livro02,
    )

    nro_inicial = iten_do_pedido["NUMERO_IMOVEL"]
    nro_final = iten_do_pedido["NUMERO_IMOVEL"]
    tipo_registro = iten_do_pedido["TIPO_IMOVEL"]
    cartorio_imovel = iten_do_pedido["NUMERO_RI"]
    # logger.info(f"LIVRO02: Criando registro no Livro 02: {iten_do_pedido}")

    models.Livro02.objects.criar_defaults()

    models.Livro05.objects.criar_defaults()

    models.Unidade.objects.criar_defaults()

    list_conversao = (
        list(range(int(nro_inicial), int(nro_final) + 1))
        if str(nro_inicial).isdigit()
        else []
    )

    # Colocar o For para o numero de protocolo
    for _, numero_registro in enumerate(list_conversao):
        # Inicio das conversoes - iMOVEL
        imovel_fb = get_registro_do_fb(
            numero_registro,
            tipo_registro,
            cartorio_imovel,
            db,
        )
        # imovel_fb = list(imovel_fb.values())

        if imovel_fb:
            # GRAVANDO O IMOVEL
            gravar_registro_importado_do_fb(imovel_fb, db)

            importar_ficha_do_fb_e_gravar_no_livro02(imovel_fb[0]["CHAVE_IMOVEIS"], db)

        models.Vinculo.objects.filter(estado_civil_id=13).update(
            estado_civil_id=0,
            tipo_regime_casamento_id=13,
        )

        models.Livro02.objects.filter(data_validade_itr="0001-01-01").update(
            data_validade_itr=None,
        )


# Inicio do Programa para converte
def converter_livro02_pelo_id_do_fb(imovel_id: int, db: FbConnection):
    # FILTrAR O IMOVEL
    try:
        # imovel = models.Livro02.objects.get(pk=imovel_id)
        imovel = models.Livro02.objects.filter(pk=imovel_id).first()

        nro_inicial = imovel.numero
        nro_final = imovel.numero
        tipo_registro = imovel.tipo
        cartorio_imovel = imovel.cartorio

    except models.Livro02.DoesNotExist:
        return None, None, None, None

    # logger.info(f"LIVRO02: Criando registro no Livro 02: {nro_inicial} {nro_final} {cartorio_imovel}")

    models.Livro02.objects.criar_defaults()
    models.Livro05.objects.criar_defaults()
    models.Unidade.objects.criar_defaults()

    # Gravar Tipos de models.Vinculo
    # list_tipos_vinculos = get_tipos_vinculos_do_fb()
    # criar_tipos_de_vinculos_importados_do_fb(list_tipos_vinculos)

    # COMENTANDO POIS ESTAVA BARRANDO A IMPORTACAO DO TEXTO
    # if nro_inicial:
    #     return None

    numeros_para_converter = [
        str(i) for i in range(int(nro_inicial), int(nro_final) + 1)
    ]

    # Colocar o For para o numero de protocolo
    for _x, numero_registro in enumerate(numeros_para_converter):
        # Inicio das conversoes - iMOVEL
        imovel_fb = get_registro_do_fb(
            numero_registro,
            tipo_registro,
            cartorio_imovel,
            db,
        )

        if imovel_fb:
            # GRAVANDO O IMOVEL
            gravar_registro_importado_do_fb(imovel_fb, db)

            importar_ficha_do_fb_e_gravar_no_livro02(imovel_fb["CHAVE_IMOVEIS"], db)

            print("Convertendo o texto: ", str(numero_registro))

        models.Vinculo.objects.filter(estado_civil_id=13).update(
            estado_civil_id=0,
            tipo_regime_casamento_id=13,
        )

    # Atualizar o CPF ou CNPJ vazio para o codigo zero
    models.Livro05.objects.filter(cpf__isnull=True).update(cpf="0")
    models.Livro05.objects.filter(cpf="").update(cpf="0")

    # ALTERACAO PARA AJUSTES DATA TRANSFERENCIA
    models.Vinculo.objects.filter(transferido_em=settings.MINDATE).update(
        transferido_em=Value(None, output_field=DateField()),
    )

    return nro_inicial, nro_final, tipo_registro, cartorio_imovel
