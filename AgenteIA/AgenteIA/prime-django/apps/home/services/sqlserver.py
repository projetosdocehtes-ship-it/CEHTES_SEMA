import logging
import os
from contextlib import contextmanager
from typing import TYPE_CHECKING

#import pymssql
# import pyodbc
from django.utils import timezone

from apps.home import models
from apps.pedidos.models import Ato
from core.utils.formatacoes import somente_numeros

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")

if TYPE_CHECKING:
    from apps.home.models import Certidao


class DuplicateKeyError(Exception):
    pass


# def get_sqlserver_db_url():
#     try:
#         username = os.getenv("SQLSERVER_DB_USER")
#         password = os.getenv("SQLSERVER_DB_PASSWORD")
#         host = os.getenv("SQLSERVER_DB_HOST")
#         os.getenv("SQLSERVER_DB_PORT")
#         dbname = os.getenv("SQLSERVER_DB_NAME")
#     except KeyError as e:
#         msg = f"Variável de ambiente {e} necessária para configuração do banco de dados SQL Server está ausente."
#         raise Exception(msg)

#     return f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={host};DATABASE={dbname};UID={username};PWD={password}"


def get_sqlserver_db_url() -> tuple[str, str, str, str]:
    try:
        username = os.getenv("SQLSERVER_DB_USER")
        password = os.getenv("SQLSERVER_DB_PASSWORD")
        host = os.getenv("SQLSERVER_DB_HOST")
        dbname = os.getenv("SQLSERVER_DB_NAME")
    except KeyError as e:
        msg = f"Variável de ambiente {e} necessária para configuração do banco de dados SQL Server está ausente."
        raise Exception(msg)

    return host, username, password, dbname


# class SqlServerConnection:
#     def __enter__(self):
#         self.connection = self.connect_db()
#         return self

#     def __exit__(self, exc_type, exc_val, exc_tb):
#         if self.connection:
#             self.connection.close()
#             print("Conexão SQLSERVER encerrada com sucesso")

#     def connect_db(self):
#         try:
#             connection_string = get_sqlserver_db_url()
#             connection = pyodbc.connect(connection_string)
#             print("Conexão SQLSERVER estabelecida com sucesso")
#             return connection
#         except pyodbc.Error as e:
#             print("Erro ao se conectar ao SQL Server", e)
#             return None

#     def query(self, sql, params=None) -> list:
#         if self.connection:
#             cursor = self.connection.cursor()
#             try:
#                 cursor.execute(sql, params or ())
#                 columns = [column[0] for column in cursor.description]
#                 results = []
#                 for row in cursor.fetchall():
#                     results.append(dict(zip(columns, row, strict=False)))
#                 return results
#             except pyodbc.Error as e:
#                 print("Erro ao executar consulta", e)
#             finally:
#                 cursor.close()
#         return None

#     def command(self, sql, params=None):
#         if self.connection:
#             cursor = self.connection.cursor()
#             try:
#                 cursor.execute(sql, params or ())
#                 self.connection.commit()
#                 return True
#             except pyodbc.Error as e:
#                 logger.error("Erro ao executar comando", e)
#                 self.connection.rollback()
#             finally:
#                 cursor.close()
#         return False

#     def transaction(self, commands: list[tuple[str, tuple | None]]) -> bool:
#         if not self.connection:
#             return False

#         try:
#             with self.connection.cursor() as cursor:
#                 cursor.execute("BEGIN TRANSACTION")
#                 for sql, params in commands:
#                     try:
#                         cursor.execute(sql, params or ())
#                     except pyodbc.Error as e:
#                         logger.error(f"Erro ao executar comando: {sql} com parâmetros: {params}, erro: {e}")
#                         self.connection.rollback()
#                         return False
#                 self.connection.commit()
#                 return True
#         except pyodbc.Error as e:
#             logger.error("Erro ao executar transação", e)  # Substitua por um logger se necessário
#             self.connection.rollback()
#             return False

# Importa a biblioteca pymssql


class SqlServerConnection:
    class NullSqlServerConnection:
        """Classe genérica que simula uma conexão quando CONECTAR_SQLSERVER está desativado."""

        def __getattr__(self, name):
            """Intercepta chamadas de método e retorna um comportamento padrão."""

            def method(*args, **kwargs) -> None:
                logger.debug(
                    f"Chamado o método {name} com {args} e {kwargs}, mas SEM conexão SQL ativa.",
                )
                return

            return method

    def __enter__(self):
        # # ALFENAS ADICIONAR CAMPOS PARA O SQLSERVER
        # from apps.cartorios.models import Cartorio

        # usar_selo_sql_server = Cartorio.objects.all().values_list(
        #     "usar_selo_sql_server",
        #     flat=True,
        # )[0]

        # if not usar_selo_sql_server == "S":

        # GERANDO BUG NO SISTEMA
        # if not settings.CONECTAR_SQLSERVER:
        #    return self.NullSqlServerConnection()

        self.connection = (
            self.connect_db()
        )  # Estabelece a conexão com o banco de dados ao entrar no contexto
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.close()  # Fecha a conexão ao sair do contexto
            logger.debug("Conexão SQLSERVER encerrada com sucesso")

    def connect_db(self):
        logger.debug("Conectando ao SQL Server")
        try:
            host, username, password, dbname = (
                get_sqlserver_db_url()
            )  # Obtém os detalhes de conexão do banco de dados
            connection = pymssql.connect(
                server=host,
                user=username,
                password=password,
                database=dbname,
            )  # Estabelece a conexão com o banco de dados usando pymssql
            logger.debug("Conexão SQLSERVER estabelecida com sucesso")
            return connection
        except pymssql.Error as e:
            logger.exception(f"Erro ao se conectar ao SQL Server: {e}")
            return None

    def execute_query(self, sql, params=None) -> list:
        if self.connection:
            cursor = self.connection.cursor()  # Cria um cursor para executar a consulta
            try:
                cursor.execute(
                    sql,
                    params or (),
                )  # Executa a consulta com os parâmetros fornecidos
                columns = [
                    column[0] for column in cursor.description
                ]  # Obtém os nomes das colunas da consulta
                results = []
                for row in cursor.fetchall():  # Obtém todas as linhas da consulta
                    results.append(
                        dict(zip(columns, row, strict=False)),
                    )  # Cria um dicionário para cada linha, associando colunas e valores
                return results
            except pymssql.Error as e:
                logger.exception(f"Erro ao executar consulta{e}")
            finally:
                cursor.close()  # Fecha o cursor
        return None

    def execute_command(self, sql: str, params: tuple | None = None) -> bool:
        if self.connection:
            cursor = self.connection.cursor()  # Cria um cursor para executar o comando
            try:
                cursor.execute(
                    sql,
                    params or (),
                )  # Executa o comando com os parâmetros fornecidos
                return True
            except pymssql.Error as e:
                logger.exception(f"Erro ao executar comando: {e}")
                return False
            finally:
                cursor.close()  # Fecha o cursor
        return False

    # def transaction(self, commands: list[tuple[str, tuple | None]]) -> bool:
    #     if not self.connection:
    #         return False

    #     try:
    #         with self.connection.cursor() as cursor:
    #             for sql, params in commands:
    #                 try:
    #                     cursor.execute(sql, params or ())  # Executa cada comando da lista de comandos
    #                 except pymssql.Error as e:
    #                     logger.info(f"Erro ao executar comando: {sql} com parâmetros: {params}, erro: {e}")
    #                     self.connection.rollback()  # Reverte a transação em caso de erro
    #                     return False
    #             self.connection.commit()  # Confirma a transação após executar todos os comandos
    #             print("Transação executada e confirmada com sucesso")
    #             return True
    #     except pymssql.Error as e:
    #         print("Erro ao executar transação", e)
    #         self.connection.rollback()  # Reverte a transação em caso de erro
    #         return False

    @contextmanager
    def transaction_scope(self):
        try:
            self.connection.autocommit(False)
            yield
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        finally:
            self.connection.autocommit(True)

    # Exemplo de uso dos métodos com a classe de contexto

    # # Consulta
    # with SqlServerConnection() as sqlserver:
    #     result = sqlserver.query("SELECT * FROM sua_tabela WHERE coluna = ?", (valor,))
    #     if result:
    #         for row in result:
    #             print(row)

    # # Comando
    # with SqlServerConnection() as sqlserver:
    #     success = sqlserver.command(
    #         "INSERT INTO sua_tabela (coluna1, coluna2) VALUES (?, ?)",
    #         (valor1, valor2),
    #     )
    #     if success:
    #         print("Inserção bem-sucedida")

    # # Transação
    # commands = [
    #     ("UPDATE sua_tabela SET coluna1 = ? WHERE id = ?", (novo_valor1, id1)),
    #     ("DELETE FROM sua_tabela WHERE id = ?", (id2,)),
    # ]
    # with SqlServerConnection() as sqlserver:
    #     transaction_success = sqlserver.transaction(commands)
    #     if transaction_success:
    #         print("Transação bem-sucedida")

    # ATUALIZAR O SELO PRINCIAL
    def set_atualizar_selo_princial(self, numero_pedido: str) -> None:
        if not numero_pedido:
            return

        result = self.execute_query(
            f"""
                SELECT COUNT(*) as total
                FROM SELOS_MOVIMENTACAO
                WHERE PROTOCOLO = '{numero_pedido}'
                AND EH_SELO_PRINCIPAL = 'S'
                AND ROTINA = '3'
            """,
        )

        # CASO NAO ENCONTRE NENHUM SELO PRINCIPAL
        if result[0]["total"] == 0:
            # ATUALIZAR O SELO PRINCIPAL
            # atualizar_eh_principal(self, int(numero_pedido))
            atualizar_eh_principal_primeiro_item(self, numero_pedido)

    def get_quantidade_de_selos_por_pedido_de_certidao_inteiro(
        self,
        numero_pedido: str,
    ) -> int:
        if not numero_pedido:
            msg = "Número do pedido de certidão não informado"
            raise ValueError(msg)

        result = self.execute_query(
            f"""
                SELECT COUNT(*) as total
                FROM SELOS_MOVIMENTACAO SM
                JOIN SELOS_ITENS SI ON SM.CHAVE_SELOS_ITENS = SI.CHAVE_SELOS_ITENS
                WHERE SM.PROTOCOLO = '{numero_pedido}'
                AND SM.ROTINA = 3
            """,
        )

        if result:
            return result[0][
                "total"
            ]  # Presumindo que result seja uma lista de dicionários.

        return 0

    def get_selo_por_pedido_de_certidao(self, numero_pedido: str) -> list:
        if not numero_pedido:
            msg = "Número do pedido de certidão não informado"
            raise ValueError(msg)

        result = self.execute_query(
            f"""
                SELECT SI.CODIGO_SEQUENCIAL_UNICO, SI.CODIGO_DE_SEGURANCA, SI.DATA_UTILIZACAO, SM.EH_SELO_PRINCIPAL
                       , SM.PROTOCOLO, SM.IDENTIFICACAO, SM.ROTINA, SM.CODIGO_FISCAL_DO_ATO, SM.TIPO_TRIBUTACAO, SM.VALOR_EMOLUMENTO
                       , SM.VALOR_FINAL_USUARIO, SM.VALOR_TFJ, SM.TX_RECOMPE, SM.TX_ISSQN
                FROM SELOS_MOVIMENTACAO SM
                JOIN SELOS_ITENS SI ON SM.CHAVE_SELOS_ITENS = SI.CHAVE_SELOS_ITENS
                WHERE SM.PROTOCOLO = '{numero_pedido}'
                AND SM.ROTINA = 3
            """,
        )
        if result:
            for row in result:
                print(row)
        return result

    def get_selo_por_protocolo(self, numero_protocolo: str) -> list:
        if not numero_protocolo:
            msg = "Número do protocolo não informado"
            raise ValueError(msg)

        result = self.execute_query(
            f"""
                SELECT SI.CODIGO_SEQUENCIAL_UNICO, SI.CODIGO_DE_SEGURANCA, SI.DATA_UTILIZACAO, SM.EH_SELO_PRINCIPAL
                       , SM.PROTOCOLO, SM.IDENTIFICACAO, SM.ROTINA, SM.CODIGO_FISCAL_DO_ATO, SM.TIPO_TRIBUTACAO, SM.VALOR_EMOLUMENTO
                       , SM.VALOR_FINAL_USUARIO, SM.VALOR_TFJ, SM.TX_RECOMPE, SM.TX_ISSQN
                FROM SELOS_MOVIMENTACAO SM
                JOIN SELOS_ITENS SI ON SM.CHAVE_SELOS_ITENS = SI.CHAVE_SELOS_ITENS
                WHERE SM.PROTOCOLO = '{numero_protocolo}'
                AND SM.ROTINA = 4
            """,
        )

        if result:
            for row in result:
                models.SeloEletronico.criar_atualizar_selos_protocolo(
                    row,
                    numero_protocolo,
                )

        return result

    def listar_selos_disponiveis(self) -> list:
        logger.info("Listando selos disponíveis")

        result = self.execute_query(
            "SELECT * FROM SELOS_ITENS WHERE DATA_UTILIZACAO IS NULL AND DATA_DESCARTE IS NULL",
        )
        if result:
            for row in result:
                print(row)
        return result

    def listar_selos_disponiveis_por_quantidade(self, quantidade: int) -> list:
        logger.info("Listando selos disponíveis")
        result = self.execute_query(
            "SELECT TOP (?) * FROM SELOS_ITENS WHERE DATA_UTILIZACAO IS NULL AND DATA_DESCARTE IS NULL",
            (quantidade,),
        )
        if result:
            for row in result:
                print(row)
        return result

    def listar_selos_usados(self) -> list:
        logger.info("Listando selos usados")

        result = self.execute_query(
            "SELECT * FROM SELOS_ITENS WHERE DATA_UTILIZACAO IS NOT NULL",
        )
        if result:
            for row in result:
                print(row)
        return result

    def usar_selo(self, id_selo: int) -> bool:
        """Atualiza a DATA_UTILIZACAO de um selo na tabela SELOS_ITENS."""
        logger.info(f"Usando selo: {id_selo}")

        try:
            command = "UPDATE SELOS_ITENS SET DATA_UTILIZACAO = GETDATE() WHERE CHAVE_SELOS_ITENS = %s AND DATA_UTILIZACAO IS NULL"
            self.execute_command(command, (id_selo,))
            return True
        except Exception as e:
            logger.info(f"Erro ao usar selo: {e}")
            return False

    def usar_selos(self, ids_selos: list[int]) -> bool:
        """Atualiza a DATA_UTILIZACAO dos selos na tabela SELOS_ITENS."""
        logger.info(f"Usando selos: {ids_selos}")

        try:
            for id_selo in ids_selos:
                command = "UPDATE SELOS_ITENS SET DATA_UTILIZACAO = GETDATE() WHERE CHAVE_SELOS_ITENS = ?"
                self.execute_command(command, id_selo)
            self.connection.commit()
            return True
        except Exception as e:
            logger.info(f"Erro ao usar selos: {e}")
            return False

    def get_proximo_selo_disponivel(self) -> dict:
        result = self.execute_query(
            "SELECT TOP 1 * FROM SELOS_ITENS WHERE DATA_UTILIZACAO IS NULL AND DATA_DESCARTE IS NULL ORDER BY CHAVE_SELOS_ITENS ASC",
        )
        if result:
            return result[0]
        return None

    def get_e_usar_proximo_selo_disponivel(self) -> dict:
        selo = self.get_proximo_selo_disponivel()
        if selo:
            self.usar_selo(selo["CHAVE_SELOS_ITENS"])
            return selo
        else:
            return {}

    def atualizar_movimentacao_selo_certidao(self, comando: str) -> bool:
        """TEMPORARIO - CRIAR MÉTODO PARA ATUALIZAR MOVIMENTAÇÃO DE SELO."""
        command = comando
        params = ()

        try:
            return self.execute_command(command, params)
        except Exception as e:
            print(e)

    def movimentar_selo_para_certidao(
        self,
        rotina: int,
        certidao: "Certidao",
        selo: dict,
    ) -> bool:
        # Verifica se o selo já foi movimentado
        selo_movimentado = self.execute_query(
            "SELECT COUNT(*) AS COUNT FROM SELOS_MOVIMENTACAO WHERE CHAVE_SELOS_ITENS = %s",
            (selo["CHAVE_SELOS_ITENS"],),
        )[0]["COUNT"]

        if selo_movimentado > 0:
            msg = "Este selo foi usado anteriormente."
            raise DuplicateKeyError(msg)

        identificacao = (
            self.execute_query(
                "SELECT MAX(IDENTIFICACAO) AS MAX FROM SELOS_MOVIMENTACAO",
            )[0]["MAX"]
            + 1
            or 1
        )

        command = (
            "INSERT INTO SELOS_MG.dbo.SELOS_MOVIMENTACAO ("
            "IDENTIFICACAO,"
            "ROTINA,"
            "SISTEMA,"
            "CODIGO_AGRUPADOR,"
            "EH_SELO_PRINCIPAL,"
            "CHAVE_SELOS_ITENS_CONSULTA,"
            "CODIGO_SERVENTIA,"
            "CODIGO_FISCAL_DO_ATO,"
            "ANO_REFERENCIA_TABELA,"
            "DATA_PRATICA_ATO,"
            "TIPO_TRIBUTACAO,"
            "VALOR_EMOLUMENTO,"
            "VALOR_TFJ,"
            "VALOR_FINAL_USUARIO,"
            "PROTOCOLO,"
            "TIPO_LIVRO,"
            "ORDEM_SEQUENCIAL,"
            "FOLHA,"
            "TIPO_DE_ESCRITURACAO,"
            "NUMERO_DE_ORDEM,"
            # "NOME_LIVRO,"
            # "ESPECIE_ESCRITURA,"
            "ESPECIE_CERTIDAO,"
            "COMPLEMENTO_CERTIDAO,"
            # "NOME_CARTORIO_ORIGEM,"
            "DETALHAMENTO_CERTIDAO,"
            "NOME_PESSOA,"
            "CPF_PESSOA,"
            "CNPJ_PESSOA,"
            # "BEM,"
            "RG_PESSOA,"
            "QUANTIDADE_FOLHAS,"
            "ESPECIE_BUSCA,"
            # "NOME_PESSOA_BUSCA,"
            # "PERIODO_BUSCA,"
            "CPF_PESSOA_BUSCA,"
            "CNPJ_PESSOA_BUSCA,"
            # "BEM_BUSCA,"
            # "DATA_EXPORTACAO,"
            # "CHAVE_SELOS_EXPORTACAO_WEB,"
            # "CHAVE_SELOS_ITENS_SUBSTITUTO,"
            "CHAVE_SELOS_ITENS,"
            "TX_RECOMPE,"
            "QUANTIDADE_PROTESTOS,"
            "TX_ISSQN"
            # "RESPONSAVEL,"
            # "QUALIFICACAO,"
            # "MAC,"
            # "TIPODOCUMENTO,"
            # "DESCRICAO_DOCUMENTO,"
            # "EMAIL_SOLICITANTE,"
            # "TIPO_DOCUMENTO_SOLICITANTE,"
            # "DOCUMENTO_SOLICITANTE,"
            # "NOME_SOLICITANTE,"
            # "ESPECIE_RECONHECIMENTO,"
            # "NomeDoServentuario
            # ")VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ")VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        )

        # PROTOCOLO
        if rotina == 4:
            params = (
                identificacao,
                rotina,  # ROTINA
                "RI",  # SISTEMA
                certidao["NUMERO_PROTOCOLO"],  # CODIGO_AGRUPADOR
                certidao["EH_SELO_PRINCIPAL"],  # EH_SELO_PRINCIPAL (Selo de Consulta)
                selo["CHAVE_SELOS_ITENS"],  # CHAVE_SELOS_ITENS_CONSULTA
                models.Configuracao.obter("codigo_serventia_tj"),  # CODIGO_SERVENTIA
                certidao["CODIGO_FISCAL"],  # CODIGO_FISCAL_DO_ATO
                timezone.now().date().year,  # ANO_REFERENCIA_TABELA
                timezone.now(),  # DATA_PRATICA_ATO
                certidao["TIPO_TRIBUTACAO"],  # TIPO_TRIBUTACAO
                certidao["VALOR_EMOLUMENTO"],  # VALOR_EMOLUMENTO
                certidao["VALOR_TFJ"],  # VALOR_TFJ
                certidao["VALOR_FINAL_USUARIO"],  # VALOR_FINAL_USUARIO
                certidao["NUMERO_PROTOCOLO"],  # PROTOCOLO
                certidao["TIPO_LIVRO"],  # TIPO_LIVRO
                certidao["ORDEM_SEQUENCIAL"],  # ORDEM_SEQUENCIAL
                0,  # FOLHA
                certidao["TIPO_DE_ESCRITURACAO"],  # TIPO_DE_ESCRITURACAO
                certidao["NUMERO_PROTOCOLO"],  # NUMERO_DE_ORDEM
                0,  # ESPECIE_CERTIDAO
                0,  # COMPLEMENTO_CERTIDAO
                "",  # DETALHAMENTO_CERTIDAO
                "",  # NOME_PESSOA
                "",  # CPF_PESSOA
                "",  # CNPJ_PESSOA
                "",  # RG_PESSOA
                0,  # QUANTIDADE_FOLHAS
                0,  # ESPECIE_BUSCA
                0,  # CPF_PESSOA_BUSCA
                0,  # CNPJ_PESSOA_BUSCA
                selo["CHAVE_SELOS_ITENS"],  # CHAVE_SELOS_ITENS
                certidao["TX_RECOMPE"],  # TX_RECOMPE
                0,  # QUANTIDADE_PROTESTOS
                certidao["TX_ISSQN"],  # TX_ISSQN
            )

        # PEDIDO DE CERTIDÃO
        if rotina == 3:
            params = (
                identificacao,
                rotina,  # ROTINA
                "RI",  # SISTEMA
                certidao.numero_pedido,  # CODIGO_AGRUPADOR
                certidao.principal,  # EH_SELO_PRINCIPAL (Selo de Consulta)
                selo["CHAVE_SELOS_ITENS"],  # CHAVE_SELOS_ITENS_CONSULTA
                models.Configuracao.obter("codigo_serventia_tj"),  # CODIGO_SERVENTIA
                somente_numeros(certidao.codigo_fiscal)[:4],  # CODIGO_FISCAL_DO_ATO
                timezone.now().date().year,  # ANO_REFERENCIA_TABELA
                timezone.now(),  # DATA_PRATICA_ATO
                str(certidao.tipo_tributacao.id)
                if certidao.tipo_tributacao
                else "1",  # TIPO_TRIBUTACAO
                certidao.emolumento_liquido_calculado,  # VALOR_EMOLUMENTO
                certidao.taxa_fiscal_judiciaria_calculada,  # VALOR_TFJ
                certidao.total,  # VALOR_FINAL_USUARIO
                certidao.numero_pedido,  # PROTOCOLO
                "402",  # TIPO_LIVRO
                "",  # ORDEM_SEQUENCIAL
                0,  # FOLHA
                1,  # TIPO_DE_ESCRITURACAO
                certidao.numero_pedido,  # NUMERO_DE_ORDEM
                # None,  # NOME_LIVRO
                # None,  # ESPECIE_ESCRITURA
                1 if certidao.id else 0,  # ESPECIE_CERTIDAO
                2 if certidao.id else 0,  # COMPLEMENTO_CERTIDAO
                # None,  # NOME_CARTORIO_ORIGEM
                "Inteiro Teor" if certidao else "outros",  # DETALHAMENTO_CERTIDAO
                certidao.nome_pessoa,  # NOME_PESSOA
                certidao.cpf_pessoa,  # CPF_PESSOA
                certidao.cnpj_pessoa,  # CNPJ_PESSOA
                # None,  # BEM
                certidao.rg_pessoa,  # RG_PESSOA
                0,  # QUANTIDADE_FOLHAS
                0,  # ESPECIE_BUSCA
                # None,  # NOME_PESSOA_BUSCA
                # None,  # PERIODO_BUSCA
                0,  # CPF_PESSOA_BUSCA
                0,  # CNPJ_PESSOA_BUSCA
                # None,  # BEM_BUSCA
                selo["CHAVE_SELOS_ITENS"],  # CHAVE_SELOS_ITENS
                certidao.recompe_calculado,  # TX_RECOMPE
                0,  # QUANTIDADE_PROTESTOS
                certidao.issqn_calculado,  # TX_ISSQN
                # None,  # RESPONSAVEL
                # None,  # QUALIFICACAO
                # None,  # MAC
                # None,  # TIPODOCUMENTO
                # None,  # DESCRICAO_DOCUMENTO
                # None,  # EMAIL_SOLICITANTE
                # None,  # TIPO_DOCUMENTO_SOLICITANTE
                # None,  # DOCUMENTO_SOLICITANTE
                # None,  # NOME_SOLICITANTE
                # None,  # ESPECIE_RECONHECIMENTO
                # None,  # NomeDoServentuario
            )

        try:
            return self.execute_command(command, params)
        except Exception as e:
            error_message = str(e)
            if (
                "Violation of PRIMARY KEY constraint" in error_message
                and "Cannot insert duplicate key" in error_message
            ):
                msg = "O selo já foi usado anteriormente."
                raise DuplicateKeyError(msg)
            logger.info(f"Erro ao movimentar selo: {e}")
            return False

    # 3	RI	Pedido de Certidão
    # 4	RI	Protocolo
    # 5	RI	Exame Cálculo

    # SELECIONAR ATO DO HOME


def selar_protocolo_sql_server_id(
    numero_protocolo: int,
    pedido_item_id: int,
    eh_selo_principal="N",
):
    print(numero_protocolo, pedido_item_id)

    # FILTRAR O PEDIDO ITEM
    ato = models.PedidoItem.objects.get(id=pedido_item_id)

    tipo_tributacao_id = 1

    try:
        with SqlServerConnection() as db, db.transaction_scope():
            selo = db.get_proximo_selo_disponivel()
            # selo = db.get_e_usar_proximo_selo_disponivel()

            if not selo:
                msg = f"Nenhum selo disponível para usar neste protocolo: {numero_protocolo}"
                print(msg)
                raise Exception(msg)

            selo_usado = db.usar_selo(selo["CHAVE_SELOS_ITENS"])

            if not selo_usado:
                msg = f"Erro ao usar selo para protocolo. Selo: {selo}"
                print(msg)
                raise Exception(msg)

            # valores individuais
            valor_emolumento = ato.valor_emolumento + ato.valor_fundo_estado
            valor_final_usuario = (
                ato.valor_emolumento + ato.valor_fundo_estado + ato.valor_tfj
            )

            # CODIGO DA TABELA - SQL SERVER
            codigo_tabela = str(ato.codigo_tabela)[:4]
            tfj = ato.valor_tfj
            fundo1_valor = ato.valor_fundo_estado
            issqn_calculado = ato.valor_tfj

            # PROTOCOLO - GERAR DICIONARIO
            certidao = {
                "NUMERO_PROTOCOLO": numero_protocolo,
                "EH_SELO_PRINCIPAL": eh_selo_principal,
                "CODIGO_FISCAL": codigo_tabela,
                "TIPO_TRIBUTACAO": tipo_tributacao_id,
                "VALOR_EMOLUMENTO": valor_emolumento,
                "VALOR_TFJ": tfj,
                "VALOR_FINAL_USUARIO": valor_final_usuario,
                "TIPO_LIVRO": 401,
                "ORDEM_SEQUENCIAL": "1-P",
                "TIPO_DE_ESCRITURACAO": 7,
                "TX_RECOMPE": fundo1_valor,
                "TX_ISSQN": issqn_calculado,
                "DATA_UTILIZACAO": timezone.now(),
            }

            selo_movimentado = db.movimentar_selo_para_certidao(4, certidao, selo)
            if not selo_movimentado:
                msg = f"Erro ao movimentar selo para certidão. Selo: {selo}"
                print(msg)
                raise Exception(msg)

        return selo

    except DuplicateKeyError as dke:
        logger.info(f"Erro ao movimentar selo: {dke}")
        return False
    except Exception as e:
        logger.info(f"Erro inesperado: {e}")
        return False


def selar_certidao(certidao: "Certidao") -> bool:
    try:
        with SqlServerConnection() as db, db.transaction_scope():
            selo = db.get_proximo_selo_disponivel()
            if not selo:
                msg = f"Nenhum selo disponível para usar nesta certidão: {certidao.qualificacao_completa}"
                print(msg)
                raise Exception(msg)

            selo_usado = db.usar_selo(selo["CHAVE_SELOS_ITENS"])
            if not selo_usado:
                msg = f"Erro ao usar selo para certidão. Selo: {selo}"
                print(msg)
                raise Exception(msg)

            # CERTIDAO
            selo_movimentado = db.movimentar_selo_para_certidao(3, certidao, selo)
            if not selo_movimentado:
                msg = f"Erro ao movimentar selo para certidão. Selo: {selo}"
                print(msg)
                raise Exception(msg)

        return True
    except DuplicateKeyError as dke:
        logger.info(f"Erro ao movimentar selo: {dke}")
        return False
    except Exception as e:
        logger.info(f"Erro inesperado: {e}")
        return False


def selar_protocolo(numero_protocolo: int, ato: Ato):
    try:
        with SqlServerConnection() as db, db.transaction_scope():
            selo = db.get_proximo_selo_disponivel()
            if not selo:
                msg = f"Nenhum selo disponível para usar neste protocolo: {numero_protocolo}"
                print(msg)
                raise Exception(msg)

            selo_usado = db.usar_selo(selo["CHAVE_SELOS_ITENS"])
            if not selo_usado:
                msg = f"Erro ao usar selo para protocolo. Selo: {selo}"
                print(msg)
                raise Exception(msg)

            # valores individuais
            # codigo_tabela, emolumento, recompe, tfj, issqn = ato.emolumento_relacionado
            valor_emolumento = (
                ato.emolumento_relacionado.valor
                + ato.emolumento_relacionado.fundo1_valor
            )
            valor_final_usuario = (
                ato.emolumento_relacionado.valor
                + ato.emolumento_relacionado.fundo1_valor
                + ato.emolumento_relacionado.taxa_fiscal_judiciaria
            )

            # CODIGO DA TABELA - SQL SERVER
            codigo_tabela = "4701"
            tfj = ato.emolumento_relacionado.taxa_fiscal_judiciaria
            fundo1_valor = ato.emolumento_relacionado.fundo1_valor
            issqn_calculado = ato.emolumento_relacionado.issqn_calculado

            # PROTOCOLO - GERAR DICIONARIO
            certidao = {
                "NUMERO_PROTOCOLO": numero_protocolo,
                "EH_SELO_PRINCIPAL": "S",
                "CODIGO_FISCAL": codigo_tabela,
                "TIPO_TRIBUTACAO": ato.tipo_tributacao_id,
                "VALOR_EMOLUMENTO": valor_emolumento,
                "VALOR_TFJ": tfj,
                "VALOR_FINAL_USUARIO": valor_final_usuario,
                "TIPO_LIVRO": 401,
                "ORDEM_SEQUENCIAL": "1-P",
                "TIPO_DE_ESCRITURACAO": 7,
                "TX_RECOMPE": fundo1_valor,
                "TX_ISSQN": issqn_calculado,
            }

            selo_movimentado = db.movimentar_selo_para_certidao(4, certidao, selo)
            if not selo_movimentado:
                msg = f"Erro ao movimentar selo para certidão. Selo: {selo}"
                print(msg)
                raise Exception(msg)

        return selo

    except DuplicateKeyError as dke:
        logger.info(f"Erro ao movimentar selo: {dke}")
        return False
    except Exception as e:
        logger.info(f"Erro inesperado: {e}")
        return False


def atualizar_eh_principal(certidao: "Certidao", numero_pedido: int) -> bool:
    try:
        with SqlServerConnection() as db, db.transaction_scope():
            comando = """ UPDATE [SELOS_MG].[dbo].[SELOS_MOVIMENTACAO]
                          SET EH_SELO_PRINCIPAL = 'S'
                          WHERE PROTOCOLO =  :numero_pedido
                          AND ROTINA = 3
            """

            comando = comando.replace(":numero_pedido", str(numero_pedido))

            db.atualizar_movimentacao_selo_certidao(comando)
        return True
    except Exception as e:
        logger.info(f"Erro inesperado: {e}")
        return False

    return None


def atualizar_eh_principal_primeiro_item(
    certidao: "Certidao",
    numero_pedido: int,
) -> bool:
    try:
        with SqlServerConnection() as db, db.transaction_scope():
            comando = """ UPDATE SELOS_MOVIMENTACAO
                          SET EH_SELO_PRINCIPAL = 'S'
                          WHERE IDENTIFICACAO = (
                            SELECT MIN(IDENTIFICACAO) AS IDENTIFICACAO
                            FROM SELOS_MOVIMENTACAO
                            WHERE PROTOCOLO =  :numero_pedido
                            AND ROTINA = '3'
                )
            """

            comando = comando.replace(":numero_pedido", str(numero_pedido))

            db.atualizar_movimentacao_selo_certidao(comando)
        return True
    except Exception as e:
        logger.info(f"Erro inesperado: {e}")
        return False

    return None


def limpar_selo(numero_selo: str) -> bool:
    try:
        with SqlServerConnection() as db, db.transaction_scope():
            comando = """
                DELETE FROM [SELOS_MG].[dbo].[SELOS_MOVIMENTACAO]
                WHERE CHAVE_SELOS_ITENS IN (
                    SELECT CHAVE_SELOS_ITENS
                    FROM [SELOS_MG].[dbo].[SELOS_ITENS]
                    WHERE CODIGO_SEQUENCIAL_UNICO = ':numero_selo'
                )
                AND CHAVE_SELOS_EXPORTACAO_WEB IS NULL
            """
            comando = str(comando).replace(":numero_selo", str(numero_selo))
            db.atualizar_movimentacao_selo_certidao(comando)

            comando = """
                    UPDATE [SELOS_MG].[dbo].[SELOS_ITENS]
                    SET DATA_UTILIZACAO = NULL
                    WHERE CODIGO_SEQUENCIAL_UNICO = ':numero_selo'

            """
            comando = str(comando).replace(":numero_selo", str(numero_selo))
            db.atualizar_movimentacao_selo_certidao(comando)

        return True
    except Exception as e:
        logger.info(f"Erro inesperado: {e}")
        return False


def atualizar_valores(certidao: "Certidao") -> bool:
    try:
        with SqlServerConnection() as db, db.transaction_scope():
            comando = """
            update SELOS_MOVIMENTACAO
            set VALOR_EMOLUMENTO = 0,
                VALOR_TFJ = 0,
                VALOR_FINAL_USUARIO = 0
            where TIPO_TRIBUTACAO = 74
            """
            db.atualizar_movimentacao_selo_certidao(comando)

            comando = """ UPDATE [SELOS_MG].[dbo].[SELOS_MOVIMENTACAO]
                        SET ORDEM_SEQUENCIAL = 'L2'
                        WHERE ORDEM_SEQUENCIAL = ''
                        AND TIPO_LIVRO > 0
                        AND ROTINA = 3
            """
            db.atualizar_movimentacao_selo_certidao(comando)

            comando = """ UPDATE [SELOS_MG].[dbo].[SELOS_MOVIMENTACAO]
                        SET   VALOR_EMOLUMENTO = 27.68, TIPO_TRIBUTACAO = 1, VALOR_FINAL_USUARIO = 37.46
                        WHERE VALOR_EMOLUMENTO = 26.11
                     """
            db.atualizar_movimentacao_selo_certidao(comando)

            comando = """ UPDATE [SELOS_MG].[dbo].[SELOS_MOVIMENTACAO]
                        SET   VALOR_EMOLUMENTO = 48.43, TIPO_TRIBUTACAO = 1, VALOR_FINAL_USUARIO = 58.21
                        WHERE VALOR_EMOLUMENTO = 45.69
                     """
            db.atualizar_movimentacao_selo_certidao(comando)

            comando = """ UPDATE [SELOS_MG].[dbo].[SELOS_MOVIMENTACAO]
                     SET   VALOR_EMOLUMENTO = 6.57, TIPO_TRIBUTACAO = 1, VALOR_FINAL_USUARIO = 8.61
                     WHERE VALOR_EMOLUMENTO = 6.20
                     """
            db.atualizar_movimentacao_selo_certidao(comando)

            comando = """ UPDATE [SELOS_MG].[dbo].[SELOS_MOVIMENTACAO]
                     SET TIPO_TRIBUTACAO = 10
                     WHERE TIPO_TRIBUTACAO = 100
                     """
            db.atualizar_movimentacao_selo_certidao(comando)

            comando = """ UPDATE [SELOS_MG].[dbo].[SELOS_MOVIMENTACAO]
                     SET TIPO_TRIBUTACAO = 10
                     WHERE VALOR_EMOLUMENTO = 0 AND VALOR_TFJ = 0 AND VALOR_FINAL_USUARIO = 0
                     """
            db.atualizar_movimentacao_selo_certidao(comando)

            comando = """ UPDATE [SELOS_MG].[dbo].[SELOS_MOVIMENTACAO]
                      SET PERIODO_BUSCA = '2019 a 2024'
                        , NOME_PESSOA_BUSCA = 'CARTORIO'
                        , ESPECIE_BUSCA = 1
                      WHERE PERIODO_BUSCA is null
                      AND TIPO_TRIBUTACAO = 10
                      AND CODIGO_FISCAL_DO_ATO = 8301
                      AND ANO_REFERENCIA_TABELA = 2024
                    """
            db.atualizar_movimentacao_selo_certidao(comando)

            comando = """
                UPDATE SELOS_MOVIMENTACAO
                SET CODIGO_FISCAL_DO_ATO = 8401
                WHERE CODIGO_FISCAL_DO_ATO = 0
            """
            db.atualizar_movimentacao_selo_certidao(comando)

            comando = """
                UPDATE [SELOS_MG].[dbo].[SELOS_MOVIMENTACAO]
                SET VALOR_EMOLUMENTO = 0,
	                VALOR_FINAL_USUARIO = 0,
                    TX_RECOMPE = 0,
	                TX_ISSQN=0
                WHERE TIPO_TRIBUTACAO = 28
                AND ANO_REFERENCIA_TABELA = 2024
                AND VALOR_EMOLUMENTO > 0
            """
            db.atualizar_movimentacao_selo_certidao(comando)

            comando = """
               UPDATE [SELOS_MG].[dbo].[SELOS_MOVIMENTACAO]
               SET  VALOR_EMOLUMENTO = 24.22,
		            VALOR_FINAL_USUARIO = 29.11,
		            VALOR_TFJ = 4.89,
                    TX_RECOMPE = 1.37,
		            TX_ISSQN=0.46
               WHERE TIPO_TRIBUTACAO in (3,4)
               AND CODIGO_FISCAL_DO_ATO = 4701
            """
            db.atualizar_movimentacao_selo_certidao(comando)

            comando = """
                UPDATE [SELOS_MG].[dbo].[SELOS_MOVIMENTACAO]
                SET VALOR_EMOLUMENTO = 0,
	                VALOR_FINAL_USUARIO = 0,
                    VALOR_TFJ = 0,
                    TX_RECOMPE = 0,
	                TX_ISSQN=0,
                    TIPO_TRIBUTACAO = 10
                WHERE TIPO_TRIBUTACAO = 5
                AND ANO_REFERENCIA_TABELA = 2024
            """
            db.atualizar_movimentacao_selo_certidao(comando)

            comando = """
                UPDATE  SELOS_MOVIMENTACAO
                SET VALOR_FINAL_USUARIO = VALOR_TFJ
                WHERE TIPO_TRIBUTACAO = 28
                AND VALOR_FINAL_USUARIO = 0
                AND VALOR_TFJ > 0
            """
            db.atualizar_movimentacao_selo_certidao(comando)

            logger.info("Atualização de valores realizada com sucesso")
        return True
    except Exception as e:
        logger.info(f"Erro inesperado: {e}")
        return False

    return None


# BUSCAR EMOLUMENTOS NO SQL SERVER
def selecionar_emolumentos_sql_server(self, comando) -> bool:
    # Verifica o comando
    return self.execute_query(comando)
