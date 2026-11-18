import configparser
import logging
import os

from apps.home.models import models_home as models
from apps.home.services import firebird
from apps.home.utils import atualizar_texto_registro_auxiliar
from core.utils.firebird_utils import FbConnection
from core.utils.formatacoes import formatar_nome, somente_numeros

logger = logging.getLogger(__name__)

# Iniciar variaveis
conn, cur = "", ""


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


def gerar_beep() -> None:
    # import winsound

    # frequency = 2500  # Define a frequência do beep
    # duration = 1000  # Define a duração do beep em milissegundos
    # winsound.Beep(frequency, duration)
    pass


# Formatar para Gravar a data corretamente
def formatar_data(data):
    if str(data) != "None":
        if str(data) != "":
            return str(data[8:10]) + "." + str(data[5:7]) + "." + str(data[0:4])
        else:
            return None
    else:
        return None


# ATUALIZAR APOS IMPORTAR
def correcoes_sistema_importacao() -> None:
    try:
        models.Livro03Ligacao.objects.filter(transferido_em="1899-01-01").update(
            transferido_em=None,
        )
    except Exception:
        logger.exception("Erro ao atualizar transferido_em: ")


# GERAR AS TABELAS BASICAS PARA IMPORTACAO
def gerar_tabelas_base_postgresql(reg_id_aux) -> None:
    list_estado_civil = firebird.importar_tipo_regime_casamento_do_fb()
    gravar_estado_civil_postegresql(list_estado_civil)

    list_imovel_vinculado = get_imoveis_vinculados_fb()
    criar_imoveis_vinculados(list_imovel_vinculado)

    # grava todas as figuras
    list_figuras = gerar_figuras()
    gravar_figuras_postegresql(list_figuras)

    # grava todas os tipos de cedulas
    list_cedulas = gerar_cedulas()
    gravar_tipos_cedulas_postegresql(list_cedulas)

    # JOGAR O ZERO COMO INICIAL
    try:
        gravar_tipos_cedulas_postegresql([{"CHAVE_TIPOS": 0, "TIPO": ""}])
    except Exception:
        # gerar_beep()
        print("Gerar tabelas basicas. Erro ao gravar o zero como inicial")

        # logger.exception("ERRO")


# Gerar todas as pessoas


def gerar_figuras(db: FbConnection):
    query = " SELECT CHAVE_FIGURAS, TIPOFIGURA FROM FIGURAS "

    db = FbConnection() if db is None else db
    return db.execute_query(query)


def importar_tipo_regime_casamento_do_fb(db: FbConnection):
    # # Tente obter o valor do cache
    # list_estado_civil = cache.get("list_estado_civil")

    # # Se não estiver no cache, busca no banco de dados
    # if list_estado_civil is None:
    # # conn = firebird.get_conexao_firebird()
    # conn = get_conexao_firebird()
    # cur = conn.cursor()

    # Comando SQL a executar
    query = " SELECT CHAVE_CATEGORIAS, TIPOCATEGORIA FROM CATEGORIAS "
    db = FbConnection() if db is None else db
    return db.execute_query(query)

    # # Executa o comando
    # cur.execute(comando)
    # resultados = cur.fetchall()
    # resultados = firebird_utils.processar_resultados_e_converter_decimal_para_int(resultados)

    # list_estado_civil = []
    # for c in resultados:
    #     list_estado_civil.append(c)

    # try:
    #     _ = list_estado_civil[0][1]
    # except Exception as e:
    #     gerar_beep()

    #     # Log do erro
    #     logger.info(f"estado_civil NAO ENCONTRADO: ")
    #     list_estado_civil = None

    # # Armazena no cache
    # cache.set("list_estado_civil", list_estado_civil, timeout=3600)

    # return list_estado_civil


def get_imoveis_vinculados_fb(db: FbConnection):
    # # Tentativa de obter os dados do cache
    # list_imovel_vinculado = cache.get("list_imovel_vinculado")

    # # Se não estiver no cache, proceder com a consulta ao banco de dados
    # if list_imovel_vinculado is None:
    #     # conn = firebird.get_conexao_firebird()
    #     conn = get_conexao_firebird()
    #     cur = conn.cursor()

    # Comando SQL a ser executado
    query = "SELECT CHAVE_IMOVEL_VINCULADO, DESC_TIPO FROM IMOVEL_VINCULADO "
    db = FbConnection() if db is None else db
    return db.execute_query(query)


#     # Executa o comando SQL
#     cur.execute(comando)
#     resultados = cur.fetchall()
#     resultados = firebird_utils.processar_resultados_e_converter_decimal_para_int(resultados)

#     list_imovel_vinculado = []
#     for c in resultados:
#         list_imovel_vinculado.append(c)

#     try:
#         _ = list_imovel_vinculado[0][1]
#     except Exception as e:
#         gerar_beep()

#         logger.info(f"imovel_vinculado NAO ENCONTRADO: ")
#         list_imovel_vinculado = None

#

#     # Armazena os dados no cache
#     cache.set("list_imovel_vinculado", list_imovel_vinculado, timeout=3600)

# return list_imovel_vinculado


def gerar_cedulas(db: FbConnection) -> list:
    # # Tentativa de obter os dados do cache
    # list_cedulas = cache.get("list_cedulas")

    # # Se não estiver no cache, proceder com a busca no banco de dados
    # if list_cedulas is None:
    #     # conn = firebird.get_conexao_firebird()
    #     conn = get_conexao_firebird()
    #     cur = conn.cursor()

    # Comando SQL a ser executado
    query = " SELECT CHAVE_TIPOS, TIPO FROM TIPOS "
    db = FbConnection() if db is None else db
    return db.execute_query(query)


#     # Executa o comando SQL
#     cur.execute(comando)
#     resultados = cur.fetchall()
#     resultados = firebird_utils.processar_resultados_e_converter_decimal_para_int(resultados)

#     list_cedulas = []
#     for c in resultados:
#         list_cedulas.append(c)

#     try:
#         _ = list_cedulas[0][1]
#     except Exception as e:
#         gerar_beep()

#         logger.info(f"CEDULA NAO ENCONTRADO: ")
#         list_cedulas = None

#

#     # Armazenar os dados no cache
#     cache.set("list_cedulas", list_cedulas, timeout=3600)

# return list_cedulas


# Gerar todas as pessoas
def get_pessoas_do_fb(list_ligacoes, db: FbConnection):
    lista_pessoas = [str(item["CHAVE_PESSOAS"]) for item in list_ligacoes]
    lista_pessoas_string = ", ".join(lista_pessoas)

    # Comando SQL a executar
    query = (
        " SELECT CHAVE_PESSOAS, CPF, NOME, NACIONALIDADE, PROFISSAO, DOCUMENTO, NOMEPAI ,       "
        "        NOMEMAE, DATA_CADASTRO, CIDADE , UF, CHAVE_CONJUGE, SEXO  , CEP,               "
        "        EMAIL, ENDERECO , DATA_NASCIMENTO, DATA_EXPEDICAO , NATURALIDADE,              "
        "        PESSOA_JURIDICA, DATA_ATUALIZACAO, TELEFONE, CHAVE_CATEGORIAS ,                "
        "        CHAVE_TIPO_REGIME , CHAVE_DOCUMENTOS, TIPO_PESSOA , NUMEROCONTROLE,            "
        "        NOME_ORIGINAL, ORGAO_EMISSOR, STATUS, DATACASAMENTO, TIPOCASAMENTO             "
        "        FROM PESSOAS where CHAVE_PESSOAS IN ("
        f"{lista_pessoas_string}"
        ")"
    )
    db = FbConnection() if db is None else db

    return db.execute_query(query)

    # # Execute the SELECT statement:
    # list_pessoas = []
    # cur.execute(comando)
    # # print("gerando nomes")

    # resultados = cur.fetchall()
    # resultados = firebird_utils.processar_resultados_e_converter_decimal_para_int(resultados)

    # cur.close()

    # list_pessoas.extend(resultados)

    # return list_pessoas


# Obter o numero a ser importado
def get_quantidade_de_registros_auxiliares_no_firebird(
    numero,
    cartorio,
    db: FbConnection,
) -> int:
    # conn = firebird.get_conexao_firebird()
    #  get_conexao_firebird()
    cartorio = cartorio or "1"
    query = f"""
        SELECT COUNT(CHAVE_REG_AUXILIARES)
        FROM   REG_AUXILIARES R
        WHERE  R.NUMERO = '{numero!s}'
        AND    R.CARTORIO = '{cartorio!s}'
    """

    db = FbConnection() if db is None else db
    resultados = db.execute_query(query)

    return resultados[0]["COUNT"] if resultados else 0


# Obter o numero a ser importado
def get_registro_id_auxiliar_do_fb(numero, cartorio, db: FbConnection) -> int:
    # conn = firebird.get_conexao_firebird()
    # get_conexao_firebird()
    # Comando SQL a executar
    query = f"""
        SELECT CHAVE_REG_AUXILIARES
        FROM   REG_AUXILIARES R
        WHERE  R.NUMERO ='{numero!s}'
        AND    R.CARTORIO = '{cartorio!s}'
        """

    # cur = conn.cursor()
    # cur.execute(comando)

    # resultados = cur.fetchone()
    # resultados = firebird_utils.processar_resultados_e_converter_decimal_para_int(resultados)

    # cur.close()
    db = FbConnection() if db is None else db
    resultados = db.execute_query(query)

    return resultados[0]["CHAVE_REG_AUXILIARES"] if resultados else 0


# Gerar protocolo a ser importado
def get_registro_auxiliar_do_fb(numero, cartorio, db: FbConnection):
    # conn = firebird.get_conexao_firebird()
    # get_conexao_firebird()

    # Comando SQL a executar
    cartorio = cartorio or "1"

    query = f"""
        SELECT CHAVE_REG_AUXILIARES, DATA_ABERTURA, PRODUTO, CHAVE_TIPOS, NUMERO,
                DATA_CANCELAMENTO, DATA_VENCIMENTO, NROCEDULA, CARTORIO, ULTIMO_LIVRO,
                ULTIMO_FOLHA, OBS, MATRICULA_CNM
        FROM   REG_AUXILIARES R
        WHERE  R.NUMERO = {numero!s}
        AND    R.CARTORIO = '{cartorio!s}'
        """

    list_auxiliar = []
    # cur.execute(query)

    # resultados = cur.fetchall()
    # resultados = firebird_utils.processar_resultados_e_converter_decimal_para_int(resultados)
    db = FbConnection() if db is None else db
    resultados = db.execute_query(query)

    list_auxiliar.extend(resultados)

    return list_auxiliar


# Gerar objetos
def gerar_objetos(reg_id_aux, cur, db: FbConnection):
    # conn = firebird.get_conexao_firebird()
    # get_conexao_firebird()

    # Comando SQL a executar
    query = (
        " SELECT CHAVE_REG_AUX_OBJETOS, CHAVE_REG_AUXILIARES, ESPECIE, ESPECIE_NUM,     "
        "        ESPECIE_DESC, ESPECIE_QTDE, VALORPRODUTO                               "
        " FROM   REG_AUX_OBJETOS WHERE CHAVE_REG_AUXILIARES = " + str(reg_id_aux)
    )

    # Execute the SELECT statement:
    list_objetos = []
    # cur.execute(comando)

    # resultados = cur.fetchall()
    # resultados = firebird_utils.processar_resultados_e_converter_decimal_para_int(resultados)

    # cur.close()  # fecha a conexao

    db = FbConnection() if db is None else db
    resultados = db.execute_query(query)

    list_objetos.extend(resultados)

    return list_objetos


# Gerar garantias
def get_garantias_do_fb(reg_id_aux, db: FbConnection):
    # conn = firebird.get_conexao_firebird()
    # get_conexao_firebird()

    # Comando SQL a executar
    query = (
        " SELECT CHAVE_REG_AUX_GARANTIAS, CHAVE_REG_AUXILIARES, ESPECIE, ESPECIE_NUM,       "
        "        ESPECIE_DESC, ESPECIE_QTDE, PENHOR, TIPO, NUMEROMAT, VALOR, FAZENDA,       "
        "        NUMEROATO, CHAVE_IMOVEL_VINCULADO, AREA                                    "
        " FROM   REG_AUX_GARANTIAS WHERE CHAVE_REG_AUXILIARES =                             "
        + str(reg_id_aux)
    )

    # cur.execute(comando)

    # resultados = cur.fetchall()
    # resultados = firebird_utils.processar_resultados_e_converter_decimal_para_int(resultados)

    # cur.close()  # fecha a conexao

    db = FbConnection() if db is None else db
    resultados = db.execute_query(query)

    list_garantias = []
    list_garantias.extend(resultados)

    return list_garantias


# Gerar ligacoes
def get_ligacoes_do_fb(registros_auxiliares, db: FbConnection):
    # chaves_reg_aux = ",".join([str(registro[0]) for registro in registros_auxiliares])
    chaves_reg_aux = registros_auxiliares[0]["CHAVE_REG_AUXILIARES"]

    query = f"""
        SELECT CHAVE_LIGACOES, CHAVE_PESSOAS, CHAVE_REG_AUXILIARES, CHAVE_FIGURAS,
                SITUACAO, DATA_TRANSFERENCIA, TIPO_ATO, NUMERO_ATO, INDICADORIMPRESSO,
                CHAVE_CATEGORIAS, OBSERVACAO, REGIME
        FROM LIGACOES
        WHERE CHAVE_REG_AUXILIARES IN ({chaves_reg_aux})
        """

    # Execute the SELECT statement:
    list_registros_auxiliares = []

    # conn = firebird.get_conexao_firebird()
    # get_conexao_firebird()
    # cur.execute(query)

    # resultados = cur.fetchall()
    # resultados = firebird_utils.processar_resultados_e_converter_decimal_para_int(resultados)

    # cur.close()  # fecha a conexao

    db = FbConnection() if db is None else db
    resultados = db.execute_query(query)

    list_registros_auxiliares.extend(resultados)

    return list_registros_auxiliares


# INICIAR PESSOAS DE GRAVAR
def criar_pessoas_do_fb(list_pessoas):
    objectos_pessoas = []

    for pessoas in list_pessoas:
        pessoa_id = str(pessoas["CHAVE_PESSOAS"])
        cpf = somente_numeros(str(pessoas["CPF"]))
        nome = formatar_nome(str(pessoas["NOME"]))
        nacionalidade = str(pessoas["NACIONALIDADE"])
        profissao = formatar_nome(str(pessoas["PROFISSAO"]))
        documento = str(pessoas["DOCUMENTO"])
        # nome_pai = formatar_nome(pessoas["NOMEPAI"])
        # nome_mae = formatar_nome(pessoas["NOMEMAE"])

        # criado_em = adicionar_fuso_horario_em_data(pessoas[8] if pessoas[8] else settings.MIN_DATE),

        # cidade        = str(pessoas[9]) if pessoas[9] else "",
        # uf            = pessoas[10] if pessoas[10] else "",
        # conjuge       = str(pessoas[11]) if pessoas[11] else None,
        # sexo          = str(pessoas[12]) if pessoas[12] else None,
        # cep           = pessoas[13] if pessoas[13] else None,
        # email         = str(pessoas[14]) if pessoas[14] else "",
        # endereco      = str(pessoas[15]) if pessoas[15] else "",
        # data_nascimento = pessoas[16] if pessoas[16] else None,
        # data_expedicao  = pessoas[17] if pessoas[17] else None,
        # naturalidade    = str(pessoas[18]).lower() if pessoas[18] else "brasileira",
        # pessoa_juridica = str(pessoas[19]) if pessoas[19] else None,
        # data_atualizacao = pessoas[20] if pessoas[20] else None,
        # telefone         = str(pessoas[21]) if pessoas[21] else "",
        #             # "tipo_regime_casamento": tipo_regime_casamento_obj,
        #             "tipo_regime": str(pessoas[23]) if pessoas[23] else None,
        #             "tipo_documento": str(pessoas[24]) if pessoas[24] else None,
        #             "tipo_pessoa": str(pessoas[25]) if pessoas[25] else None,
        #             "numero_controle": str(pessoas[26]) if pessoas[26] else None,
        #             "nome_original": str(pessoas[27]) if pessoas[27] else None,
        #             "orgao_emissor": str(pessoas[28]) if pessoas[28] else None,
        #             "situacao": str(pessoas[29]) if pessoas[29] else None,
        #             "data_casamento": pessoas[30] if pessoas[30] else None,
        #             "tipo_casamento": str(pessoas[31]) if pessoas[31] else None,

        print("PESSOA: Tentando criar pessoa : ", pessoa_id)

        try:
            pessoa, created = models.Livro05.objects.update_or_create(
                id=pessoa_id,
                defaults={
                    "cpf": cpf,
                    "nome": nome,
                    "nacionalidade": nacionalidade,
                    "profissao": profissao,
                    "documento": documento,
                    # "nome_pai": nome_pai,
                    # "nome_mae": nome_mae,
                    # # "criado_em": adicionar_fuso_horario_em_data(pessoas[8] if pessoas[8] else settings.MIN_DATE),
                    # "cidade": str(pessoas[9]) if pessoas[9] else "",
                    # "uf": pessoas[10] if pessoas[10] else "",
                    # "conjuge": str(pessoas[11]) if pessoas[11] else None,
                    # "sexo": str(pessoas[12]) if pessoas[12] else None,
                    # "cep": pessoas[13] if pessoas[13] else None,
                    # "email": str(pessoas[14]) if pessoas[14] else "",
                    # "endereco": str(pessoas[15]) if pessoas[15] else "",
                    # "data_nascimento": pessoas[16] if pessoas[16] else None,
                    # "data_expedicao": pessoas[17] if pessoas[17] else None,
                    # "naturalidade": str(pessoas[18]).lower() if pessoas[18] else "brasileira",
                    # "pessoa_juridica": str(pessoas[19]) if pessoas[19] else None,
                    # "data_atualizacao": pessoas[20] if pessoas[20] else None,
                    # "telefone": str(pessoas[21]) if pessoas[21] else "",
                    # # "tipo_regime_casamento": tipo_regime_casamento_obj,
                    # "tipo_regime": str(pessoas[23]) if pessoas[23] else None,
                    # "tipo_documento": str(pessoas[24]) if pessoas[24] else None,
                    # "tipo_pessoa": str(pessoas[25]) if pessoas[25] else None,
                    # "numero_controle": str(pessoas[26]) if pessoas[26] else None,
                    # "nome_original": str(pessoas[27]) if pessoas[27] else None,
                    # "orgao_emissor": str(pessoas[28]) if pessoas[28] else None,
                    # "situacao": str(pessoas[29]) if pessoas[29] else None,
                    # "data_casamento": pessoas[30] if pessoas[30] else None,
                    # "tipo_casamento": str(pessoas[31]) if pessoas[31] else None,
                },
            )
            objectos_pessoas.append(pessoa)
            logger.info(f"PESSOA: inserida : {pessoa!s}")
        except Exception:
            logger.exception(f"ERRO ao criar pessoa {pessoas[0]}")

    return objectos_pessoas or None


## INICIAR PROCESSOS DE GRAVAR
def criar_registros_auxiliares(list_numero, db: FbConnection):
    registros = []
    for numero_lista in list_numero:
        print(
            "Verificar registro auxiliar número : ",
            numero_lista["CHAVE_REG_AUXILIARES"],
        )

        registro_auxiliar_id = numero_lista["CHAVE_REG_AUXILIARES"]
        data_abertura = numero_lista["DATA_ABERTURA"]
        cancelado_em = numero_lista["DATA_CANCELAMENTO"]
        data_vencimento = numero_lista["DATA_VENCIMENTO"]
        numero_cedula = numero_lista["NROCEDULA"]
        cartorio = numero_lista["CARTORIO"]
        ultimo_livro = numero_lista["ULTIMO_LIVRO"]
        ultimo_folha = numero_lista["ULTIMO_FOLHA"]
        observacao = numero_lista["OBS"]
        cnm = ""

        descricao = str(numero_lista["PRODUTO"]).title()
        cedula_id = str(numero_lista["CHAVE_TIPOS"]).split(".")[0]
        numero = str(numero_lista["NUMERO"]).split(".")[0]

        observacao = observacao if observacao else ""

        try:
            registro, created = models.Livro03.objects.update_or_create(
                pk=registro_auxiliar_id,
                defaults={
                    "data_abertura": data_abertura,
                    "descricao": descricao,
                    "tipo_registro_auxiliar_id": cedula_id,
                    "numero": numero,
                    "cancelado_em": cancelado_em,
                    "data_vencimento": data_vencimento,
                    "numero_cedula": numero_cedula,
                    "cartorio": cartorio,
                    "ultimo_livro": ultimo_livro,
                    "ultimo_folha": ultimo_folha,
                    "observacao": observacao,
                    "cnm": cnm,
                },
            )

            registros.append(registro)

            # livro03_fb = get_livro03_do_fb(id)
            livro03_fb = atualizar_texto_registro_auxiliar.get_livro03_do_fb(
                registro_auxiliar_id,
                db,
            )
            if livro03_fb:
                try:
                    # texto_html = conveter_texto_livro03_do_fb(livro03_fb.get("FICHA"))
                    texto_html = (
                        atualizar_texto_registro_auxiliar.conveter_texto_livro03_do_fb(
                            livro03_fb[0]["FICHA"],
                        )
                    )
                except Exception as e:
                    texto_html = None
                    logger.exception(f"ERRO ao converter RTF para HTML {e}")

                if texto_html:
                    atualizar_texto_registro_auxiliar.atualizar_texto_livro03(
                        texto_html,
                        data_abertura,
                        registro_auxiliar_id,
                    )
                    print("REGISTRO AUXILIAR: Atualizado : ", registro_auxiliar_id)
                else:
                    logger.error("ERRO ao converter RTF para HTML")

                print("REGISTRO AUXILIAR: Inserido : ", id)
            else:
                print("REGISTRO AUXILIAR: Não encontrado no Firebird: ", id)

        except Exception as e:
            # gerar_beep()

            print("REGISTRO AUXILIAR NAO ENCONTRADO:")

            logger.exception(
                f"ERRO ao criar registro auxiliar {registro_auxiliar_id}. Detalhes: {e!s}",
            )

    return registros


# GRAVAR OBJETOS
def gravar_objetos_postegresql(reg_id_aux, cur) -> None:
    pass


# GRAVAR GARANTIAS
def criar_garantias_no_sistemas(garantias_fb):
    objetos_garantias = []

    for garantia in garantias_fb:
        numero_registro, tipo_registro = 0, ""

        if garantia["NUMEROMAT"]:
            numero_registro = str(garantia["NUMEROMAT"])

        if garantia["TIPO"]:
            tipo_registro = str(garantia["TIPO"])

        pk = garantia["CHAVE_REG_AUX_GARANTIAS"]
        registro_auxiliar_id = garantia["CHAVE_REG_AUXILIARES"]
        especie = str(garantia["ESPECIE"])
        numero = str(garantia["ESPECIE_NUM"])
        descricao = str(garantia["ESPECIE_DESC"])
        str(1)
        grau_penhor = str(garantia["PENHOR"])
        tipo_registro = tipo_registro
        numero_registro = numero_registro
        valor = str(garantia["VALOR"])
        fazenda = str(garantia["FAZENDA"])
        tipo_ato = str(garantia["TIPO"])
        garantia["NUMEROMAT"]
        area = str(garantia["AREA"])

        auxiliar_garantis, created = models.Livro03Garantia.objects.update_or_create(
            id=pk,
            defaults={
                "id": pk,
                "registro_auxiliar_id": registro_auxiliar_id,
                "especie": especie,
                "numero": numero,
                "descricao": descricao,
                "quantidade": str(1),
                "grau_penhor": grau_penhor,
                "tipo_registro": tipo_registro,
                "numero_registro": numero_registro,
                "valor": valor,
                "fazenda": fazenda,
                "tipo_ato": tipo_ato,
                # "imovel_vinculado_id": imovel_vinculado_id,
                "area": area,
            },
        )
        objetos_garantias.append(auxiliar_garantis)
        print("GARANTIAS: inserido garantias : ", id)

    return objetos_garantias


# GRAVAR LIGACOES
def criar_ligacoes_no_sistemas(ligacoes_fb):
    lista_ligacao = [item["CHAVE_LIGACOES"] for item in ligacoes_fb]

    # Excluir ligações atuais.
    models.Livro03Ligacao.objects.filter(id__in=lista_ligacao).delete()

    objetos_ligacoes = []
    # criar novas ligações
    for ligacoes in ligacoes_fb:
        if not ligacoes["CHAVE_LIGACOES"]:
            continue
        try:
            obj, created = models.Livro03Ligacao.objects.update_or_create(
                pk=ligacoes["CHAVE_LIGACOES"],
                defaults={
                    "pessoa_id": ligacoes["CHAVE_PESSOAS"] or 0,
                    "registro_auxiliar_id": ligacoes["CHAVE_REG_AUXILIARES"] or 0,
                    "figuras_id": ligacoes["CHAVE_FIGURAS"] or 0,
                    "situacao": (
                        str(ligacoes["SITUACAO"]) if ligacoes["SITUACAO"] else ""
                    ),
                    "transferido_em": (
                        ligacoes["DATA_TRANSFERENCIA"]
                        if ligacoes["DATA_TRANSFERENCIA"]
                        else None
                    ),
                    "tipo_ato": (
                        str(ligacoes["TIPO_ATO"]) if ligacoes["TIPO_ATO"] else "R"
                    ),
                    "numero_ato": (
                        str(ligacoes["NUMERO_ATO"]) if ligacoes["NUMERO_ATO"] else 0
                    ),
                    "observacao": (
                        str(ligacoes["OBSERVACAO"]) if ligacoes["OBSERVACAO"] else ""
                    ),
                    "regime": str(ligacoes["REGIME"]) if ligacoes["REGIME"] else "",
                    "estado_civil_id": (
                        ligacoes["CHAVE_CATEGORIAS"]
                        if ligacoes["CHAVE_CATEGORIAS"]
                        else 0
                    ),
                },
            )
            print("LIGAÇÕES: Criado ")

            # ligacao.update(transferido_em="")
            objetos_ligacoes.append(obj)
        except Exception as e:
            logger.exception(f"ERRO criar_ligacoes_no_sistemas: {e}")

    return objetos_ligacoes


# GRAVAR IMOVEL VINCULADO
def gravar_estado_civil_postegresql(list_estado_civil) -> None:
    for estado_civil in list_estado_civil:
        id = str(estado_civil[0]).split(".")[0]
        descricao = str(estado_civil[1])

        if models.EstadoCivil.objects.filter(id=id).exists():
            models.EstadoCivil.objects.filter(id=id).update(
                descricao=descricao,
            )
        else:
            models.EstadoCivil.objects.create(
                id=id,
                descricao=descricao,
            )


# GRAVAR IMOVEL VINCULADO
def criar_imoveis_vinculados(list_imovel_vinculado):
    objetos_imovel_vinculado = []
    for imovel_vinculado in list_imovel_vinculado:
        imovel_vinculado = list(
            imovel_vinculado.values(),
        )  # Converte o dicionário para lista para acessar pelo índice

        imovel_id = imovel_vinculado[0]
        descricao = str(imovel_vinculado[1])
        imovel, created = models.RegistroVinculado.objects.update_or_create(
            id=imovel_id,
            defaults={"descricao": descricao},
        )

        if created:
            logger.info(f"IMOVEL VINCULADO: Criado : {imovel_id}")
        else:
            logger.info(f"IMOVEL VINCULADO: Atualizado : {imovel_id}")

        objetos_imovel_vinculado.append(imovel_id)
        print("Incluido o numero: ", imovel_id)

    return objetos_imovel_vinculado


# GRAVAR FIGURAS DE CEDULAS
def gravar_figuras_postegresql(list_figuras) -> None:
    for item in list_figuras:
        item = list(
            item.values(),
        )  # Converte o dicionário para lista para acessar pelo índice
        id = str(item[0]).split(".")[0]
        tipo_figura = str(item[1])

        if models.Livro03Descricao.objects.filter(id=id).exists():
            models.Livro03Descricao.objects.filter(id=id).update(
                tipo_figura=tipo_figura,
            )
        else:
            models.Livro03Descricao.objects.create(
                id=id,
                tipo_figura=tipo_figura,
            )


# GRAVAR TIPOS DE CEDULAS
def gravar_tipos_cedulas_postegresql(cedulas: list) -> None:
    for cedula in cedulas:
        cedula = list(
            cedula.values(),
        )  # Converte o dicionário para lista para acessar pelo índice
        cedula_id = str(cedula[0])
        cedula_nome = str(cedula[1])
        if models.TipoRegistroAuxiliar.objects.filter(id=cedula_id).exists():
            models.TipoRegistroAuxiliar.objects.filter(id=cedula_id).update(
                nome=cedula_nome,
            )
        else:
            models.TipoRegistroAuxiliar.objects.create(id=id, nome=cedula_nome)


# INICIAR A IMPORTACAO DO LIVRO 3 PELO NUMERO - PEGANDO O ID
def importar_livro03_do_fb(pedido_item_fb, db: FbConnection) -> bool:
    nro_inicial = pedido_item_fb["NUMERO_IMOVEL"]
    nro_final = pedido_item_fb["NUMERO_IMOVEL"]
    pedido_item_fb["TIPO_IMOVEL"]
    cartorio = pedido_item_fb["NUMERO_RI"]

    print()
    logger.info(f"LIVRO 03 : Criando registro: {nro_inicial} ")

    numeros = list(range(int(nro_inicial), int(nro_final) + 1))

    # LIMPAR O REGISTRO PARA JOGAR TUDO NOVAMENTA
    for numero in numeros:
        db = FbConnection()

        quantidade = get_quantidade_de_registros_auxiliares_no_firebird(
            numero,
            cartorio,
            db=db,
        )

        if quantidade > 0:
            # OBTER O DO REGISTRO AUXILIAR
            registro_id_auxiliar = get_registro_id_auxiliar_do_fb(
                numero=numero,
                cartorio=cartorio,
                db=db,
            )

            models.Livro03Garantia.objects.filter(
                registro_auxiliar_id=registro_id_auxiliar,
            ).delete()

            models.Livro03Ligacao.objects.filter(
                registro_auxiliar_id=registro_id_auxiliar,
            ).delete()

            models.Livro03.objects.filter(id=registro_id_auxiliar).delete()

            # grava todas os imoveis vinculados
            list_imovel_vinculado = get_imoveis_vinculados_fb(db)
            criar_imoveis_vinculados(list_imovel_vinculado)

            # grava todas as figuras
            print("Gravar: figuras")
            list_figuras = gerar_figuras(db)
            gravar_figuras_postegresql(list_figuras)

            # grava todas os tipos de cedulas
            print("Gravar: cedulas")
            list_cedulas = gerar_cedulas(db)
            gravar_tipos_cedulas_postegresql(list_cedulas)

            # JOGAR O ZERO COMO INICIAL
            print("Gravar: CHAVE_TIPOS")
            # gravar_tipos_cedulas_postegresql([{"CHAVE_TIPOS": 0, "TIPO": ""}])

            # Colocar o For para o numero de protocolo
            for _, numero_reg_aux in enumerate(numeros):
                # Inicio das conversoes - iMOVEL
                list_reg_aux = get_registro_auxiliar_do_fb(
                    numero_reg_aux,
                    cartorio=cartorio,
                    db=db,
                )
                print("Gravar: LISTA DE REGISTRO AUXILIAR")

                if list_reg_aux:
                    print("Gravar: LISTA DE LIGACOES")
                    list_ligacoes = get_ligacoes_do_fb(list_reg_aux, db)

                    if list_ligacoes:
                        print("Gravar: LISTA DE PESSOAS")
                        list_pessoas = get_pessoas_do_fb(list_ligacoes, db)

                        if list_pessoas:
                            print("Gravar: LISTA DE LIGACOES E PESSOAS")
                            criar_pessoas_do_fb(list_pessoas)

                    registros_auxiliares = criar_registros_auxiliares(list_reg_aux, db)
                    if registros_auxiliares:
                        # gRAVAR LIGACOES
                        print("Gravar: LISTA DE LIGACOES 2")
                        ligacoes_fb = get_ligacoes_do_fb(list_reg_aux, db)
                        if ligacoes_fb:
                            criar_ligacoes_no_sistemas(ligacoes_fb)

                        garantias_fb = []
                        for registro in registros_auxiliares:
                            print("Gravar: LISTA DE GARANTIAS")
                            garantias_fb = get_garantias_do_fb(registro.id, db)

                        if garantias_fb:
                            print("Gravar: LISTA DE GARANTIAS 2")
                            criar_garantias_no_sistemas(garantias_fb)

                        # FAZER CORRECOES
                        print("Gravar: CORRECOES")
                        correcoes_sistema_importacao()

    return True
