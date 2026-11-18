from decimal import Decimal
import logging
from django.utils import timezone


try:
    import sqlparse
except ImportError:
    print("O módulo 'sqlparse' não está instalado. Instale-o com 'pip install sqlparse'.")

import firebirdsql
from django.conf import settings

logger = logging.getLogger(__name__)


# class FbConnection:
#     _instance = None

#     def __new__(cls):
#         if cls._instance is None:
#             cls._instance = super().__new__(cls)
#             cls._instance._logado = False
#             cls._instance._conn = None
#             cls._instance._cur = None
#             logger.warning("Criando uma nova instância de FbConnection.")
#         return cls._instance

#     def _connect(self):
#         if not self._logado:
#             #logger.warning("Tentando estabelecer uma nova conexão.")
#             try:
#                 self._conn = firebirdsql.connect(
#                     host=DB_FB_HOST,
#                     database=DB_FB_DATABASE,
#                     port=DB_FB_PORT,
#                     user=DB_FB_USER,
#                     password=DB_FB_PASS,
#                     charset=DB_FB_CHARSET,
#                 )
#                 self._cur = self._conn.cursor()
#                 self._logado = True
#                 #logger.info("Conexão com o banco de dados estabelecida.")
#             except Exception as e:
#                 logging.exception("Falha ao conectar ao banco de dados: {}".format(e))
#                 raise ConnectionError("Não foi possível conectar ao banco de dados.")


class FbConnection:
    def __init__(self):
        self._conn = None
        self._cur = None
        self.connect()

    def connect(self):
        try:
            self._conn = firebirdsql.connect(
                host=settings.DB_FB_HOST or "localhost",
                database=settings.DB_FB_DATABASE or "C:/BASE/MG-MONTE CARMELO/RICS.GDB",
                port=settings.DB_FB_PORT or 3050,
                user=settings.DB_FB_USER or "SYSDBA",
                password=settings.DB_FB_PASS or "masterkey",
                charset=settings.DB_FB_CHARSET or "ISO8859_1",
            )
            self._cur = self._conn.cursor()
            logger.info("FIREBIRD: Conexão com o banco de dados estabelecida.")
        except Exception as e:
            logging.exception(f"FIREBIRD: Falha ao conectar ao banco de dados: {e}")
            raise

    def _ensure_connection(self):
        if self._conn is None:
            self.connect()

    def commit(self):
        logger.debug("FIREBIRD: Efetuando commit...")
        self._ensure_connection()
        try:
            self._conn.commit()
        except Exception as e:
            logging.exception("Falha ao efetuar commit")
            raise

    def begin_transaction(self):
        logger.info("FIREBIRD: Iniciando transação...")
        self._ensure_connection()
        self._conn.begin()

    def rollback(self):
        logger.debug("FIREBIRD: Efetuando rollback...")
        self._ensure_connection()
        try:
            self._conn.rollback()
        except Exception as e:
            logging.exception("Falha ao efetuar rollback")
            raise

    def close(self):
        if self._conn:
            try:
                if hasattr(self._conn, "_transaction") and self._conn._transaction:
                    logger.debug("FIREBIRD: Efetuando commit antes de fechar a conexão...")
                    self.commit()
                self._conn.close()
                logger.debug("FIREBIRD: Conexão fechada")
            except Exception:
                pass
            finally:
                self._conn = None
                self._cur = None

    def rollback(self):
        logger.info("FIREBIRD: Efetuando rollback...")
        self._ensure_connection()
        self._conn.rollback()

    def execute_query(self, query: str, params: str = None) -> list:
        self._ensure_connection()
        try:
            # Parse e formata a query SQL
            formatted_query = (
                sqlparse.format(query, reindent=True, keyword_case="upper")
                        .replace("\n", " ")
                        .replace("  ", " ")
                        .replace("  ", " ")
                        .replace("  ", " ")
            )

            if params:
                logging.debug(
                "Firebird Executando:\n"
                f"QUERY:\n {formatted_query}\n\n"
                f"PARAMETROS:\n {params}\n\n"
                )

                self._cur.execute(formatted_query, params)
            else:
                logging.debug(
                    "Firebird Executando:\n"
                    "QUERY:"
                    f"{formatted_query}\n\n"
                )

                self._cur.execute(formatted_query)



            # Recupera os nomes das colunas
            colunas = [desc[0] for desc in self._cur.description]

            # Obtém todos os resultados da query
            resultados = self._cur.fetchall()

            logging.debug(f"QUERY executada com sucesso. Registros obtidos: {len(resultados)}")

            # Converte os decimais para inteiros
            resultados = processar_resultados_e_converter_decimal_para_int(resultados)

            # resultados = adicionar_timezone(resultados)

            if resultados:
                saida = [dict(zip(colunas, row)) for row in resultados]
                logging.debug(
                    "Resultado da QUERY: \n"
                    f"{saida}"
                    "\n\n"
                )
                # Converte os resultados em uma lista de dicionários e retorna
                return saida


            # Retorna lista vazia se não houver resultados
            logging.debug("Nenhum resultado encontrado.")
            return []

        except Exception as e:
            logging.exception(
                "\n"
                f"ERRO ao executar a query: {e}"
                "\n"
            )
            raise

    def execute_command(self: "FbConnection", command: str, params=None) -> None:
        self._ensure_connection()
        try:
            # Add current datetime to the command if needed
            # updated_command = _add_current_datetime_to_command(command)

            # Parse e formata o comando SQL
            formatted_command = (
                sqlparse.format(command, reindent=True, keyword_case="upper")
                .replace("\n", " ")
                .replace("  ", " ")
            )

            if params:
                logging.debug(
                    f"Executando COMANDO:\n {formatted_command!s} \n\n"
                    f"Com PARAMETROS:\n {params} \n\n"
                )

                self._cur.execute(formatted_command, params)
            else:
                logging.debug(f"""Executando COMANDO: \n {formatted_command!s} \n\n""")
                self._cur.execute(formatted_command)


            # Retorna o número de registros afetados
            affected_rows = self._cur.rowcount


            logging.debug(
                f"COMANDO executado com sucesso.\n"
                f"Registros afetados: {affected_rows}\n\n"
            )

            return affected_rows
        except Exception as e:
            self._conn.rollback()
            logging.exception(
                "\n"
                f"ERRO ao executar comando: {e}"
                "\n"
                )
            raise

    def __enter__(self):
        self._ensure_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

        # if self._conn:
        #     try:
        #         if exc_type is not None:
        #             # Se o bloco with saiu devido a uma exceção, faz rollback
        #             self._conn.rollback()
        #             logger.warning("FIREBIRD: Rollback efetuado.")
        #         else:
        #             # Se não houve exceções, tenta fazer commit
        #             # Isso pode lançar uma exceção se não houver transação ativa, então esteja preparado para capturar essa exceção
        #             try:
        #                 self._conn.commit()
        #                 logger.info("FIREBIRD: Commit efetuado.")
        #             except Exception:
        #                 logging.exception(
        #                     "FIREBIRD: Falha ao fazer commit; possívelmente não haviam transações ativas."
        #                 )
        #     except Exception as e:
        #         logging.exception("FIREBIRD: ERRO ao finalizar a operação no banco de dados")
        #         raise
        #     finally:
        #         # Tenta fechar a conexão somente depois de resolver a transação
        #         if self._conn is not None:
        #             try:
        #                 self._conn.close()
        #                 logger.info("FIREBIRD: Conexão fechada.")
        #             except Exception as e:
        #                 logging.exception(f"FIREBIRD: Erro ao tentar fechar a conexão com o banco de dados: ")
        #                 raise  # Repassa a exceção para alertar sobre o erro ao fechar a conexão
        #             finally:
        #                 # Limpa o estado do objeto após a tentativa de fechar a conexão
        #                 self._logado = False
        #                 self._conn = None
        #                 logger.info("FIREBIRD: Conexão fechada e estado de login resetado")

    # def executar_select(self, query, max_tentativas=3, delay=2) -> list:
    #     tentativa = 0
    #     while tentativa < max_tentativas:
    #         try:
    #             # db = FbConnection() if db is None else db
    #             self._ensure_connection()  # Garante que a conexão esteja ativa
    #             self._cur.execute(query)  # Executa a query

    #             colunas = [desc[0] for desc in self._cur.description]  # Recupera os nomes das colunas
    #             resultados = self._cur.fetchall()  # Obtém todos os resultados da query

    #             # Opcionalmente, converte os decimais para inteiros, se definido em outra parte do seu código
    #             resultados = processar_resultados_e_converter_decimal_para_int(resultados)

    #             if resultados:
    #                 # if len(resultados) == 0:
    #                 #     return dict(zip(colunas, resultados[0]))  # Retorna um único dicionário diretamente
    #                 # else:
    #                 return [dict(zip(colunas, row)) for row in resultados]  # Lista de dicionários
    #             return []  # Retorna lista vazia se não houver resultados

    #         except Exception as e:
    #             logger.exception(f"FIREBIRD: ERRO ao executar SELECT: {query}")
    #             logger.warning(f"Tentativa {tentativa + 1} de {max_tentativas} falhou")
    #             time.sleep(delay)  # Intervalo antes de tentar novamente
    #             tentativa += 1  # Incrementa o contador de tentativas

    #         finally:
    #             if self._conn is not None:
    #                 self.__exit__(None, None, None)  # Encerra a conexão adequadamente
    #     msg = f"FIREBIRD: Número máximo de tentativas alcançado. Falha ao executar a query.: {query}"
    #     logger.error(msg)
    #     raise ValueError(msg)
    #     return None

    def now(self) -> str:
        return self.datahora()

    def sequence(self, nome_sequence: str) -> "_Sequence":
        # Método fábrica para criar instâncias de _Sequence
        return self._Sequence(self, nome_sequence)

    # def contador(item=str):
    #     if item:
    #         query = "SELECT " + str(item).upper() + " FROM CONTADOR"
    #     else:
    #         return None

    #     try:
    #         db = FbConnection() if db is None else db
    #         resultado = db.execute_query(query)[0]
    #         # converter o dict em uma lista para retornar o valor
    #         results = list(resultado.values())[0]

    #         if not results:
    #             logging.warning(f"Nenhum resultado retornado na query de {item}.")
    #             return None
    #     except Exception:
    #         logging.exception(f"ERRO ao obter {item}")
    #         return None

    #     return results

    class _Sequence:
        def __init__(self, parent: "FbConnection", nome_sequence: str):
            self.parent = parent
            self.nome_sequence = nome_sequence
            logger.debug(f"Sequência '{self.nome_sequence}' inicializada.")

        @property
        def proximo(self) -> int:
            query = f"SELECT GEN_ID({self.nome_sequence}, 1) FROM RDB$DATABASE"
            logger.debug(f"Executando query para próximo valor da sequência: {query}")
            resultado = self.parent.execute_query(query)
            logger.debug(f"Resultado da query para próximo valor: {resultado}")

            if resultado and len(resultado) > 0:
                proximo_valor = resultado[0]["GEN_ID"]
                logger.debug(f"Próximo valor da sequência '{self.nome_sequence}': {proximo_valor}")
                return proximo_valor
            else:
                logger.warning("Nenhum resultado encontrado ou falha na query para próximo valor.")
                return None

        @property
        def atual(self) -> int:
            query = f"SELECT GEN_ID({self.nome_sequence}, 0) FROM RDB$DATABASE"
            logger.debug(f"Executando query para valor atual da sequência: {query}")
            resultado = self.parent.execute_query(query)
            logger.debug(f"Resultado da query para valor atual: {resultado}")

            if resultado and len(resultado) > 0:
                valor_atual = resultado[0]["GEN_ID"]
                logger.debug(f"Valor atual da sequência '{self.nome_sequence}': {valor_atual}")
                return valor_atual
            else:
                logger.warning("Nenhum resultado encontrado ou falha na query para valor atual.")
                return None

        def alinhar(self, field_name: str, table_name: str) -> None:
            query = f"SELECT MAX({field_name}) FROM {table_name}"
            logger.debug(f"Executando query para alinhar sequência com campo '{field_name}' na tabela '{table_name}': {query}")
            resultado = self.parent.execute_query(query)
            logger.debug(f"Resultado da query para alinhar sequência: {resultado}")

            if resultado and len(resultado) > 0:
                ultimo_id = resultado[0]["MAX"]
                logger.debug(f"Último ID encontrado na tabela '{table_name}': {ultimo_id}")

                if self.atual != ultimo_id:
                    command = f"ALTER SEQUENCE {self.nome_sequence} RESTART WITH {ultimo_id}"
                    logger.debug(f"Executando comando para reiniciar sequência '{self.nome_sequence}' com o valor {ultimo_id}: {command}")
                    self.parent.execute_command(command)
                    logger.info(f"Sequência '{self.nome_sequence}' reiniciada com sucesso para o valor {ultimo_id}.")
                else:
                    logger.debug(f"A sequência '{self.nome_sequence}' já está alinhada com o valor atual {ultimo_id}.")
            else:
                logger.warning(f"Não foi possível encontrar um valor máximo para o campo '{field_name}' na tabela '{table_name}'.")

    def get_current_value_sequence(self, nome_sequence) -> int:
        """
        Obtem o valor atual da sequence sem alterá-la.
        """

        if not nome_sequence:
            raise ValueError("Parâmetros inválidos para obter o valor atual da sequence.")

        query = f" SELECT GEN_ID({nome_sequence}, 0) FROM RDB$DATABASE "
        resultado = self.execute_query(query)
        if resultado and len(resultado) > 0:
            return resultado[0]["GEN_ID"]

        logger.warning("Nenhum resultado encontrado ou falha na query.")

        return None

    def alinhar_e_get_sequence(self, table_name: str, field_name: str, sequence_name: str) -> int:
        """
        Alinha a sequence para o valor máximo do campo em uma tabela
        """
        if not table_name or not field_name or not sequence_name:
            raise ValueError("Parâmetros inválidos para ajustar e obter a sequence.")

        try:
            query = f"SELECT MAX({field_name}) FROM {table_name}"
            response = self.execute_query(query)

            if response[0]["MAX"] == None:
                current_value = self.sequence(sequence_name).atual
                max_valor = current_value
            else:
                max_valor = int(response[0]["MAX"])
                current_value = self.sequence(sequence_name).atual

            if current_value != max_valor:
                adjustment_query = f"ALTER SEQUENCE {sequence_name} RESTART WITH {max_valor}"
                self.execute_command(adjustment_query)

            return self.sequence(sequence_name).proximo
        except Exception as e:
            logger.error(f"Erro ao ajustar e obter a sequence: ")
            return None

    def data(self):
        return timezone.now().strftime(settings.DATE_FIREBIRD_FORMAT)

    def hoje(self):
        return self.data()

    def today(self):
        return self.data()


    @property
    def data_str(self):
        return f"'{timezone.now().strftime(settings.DATE_FIREBIRD_FORMAT)}'"

    def datahora(self):
        return timezone.localtime(timezone.now()).strftime(settings.DATETIME_FIREBIRD_FORMAT)


GLOBAL_CONN = None
# if __name__ == "__main__":
#     db = FbConnection() if db is None else db
#     db.begin_transaction()
#     try:
#         # Aqui, você pode colocar suas operações no banco de dados
#         results = db.execute_query("SELECT CURRENT_DATE FROM RDB$DATABASE")
#         logger.info(f"A data atual do banco é: {results[0][0]}")
#         db.commit()
#     except Exception as e:
#         db.rollback()


def processar_resultados_e_converter_decimal_para_int(result) -> list:
    """
    Processa os resultados obtidos e converte
    os decimais despresiveis (terminados em 00) para inteiros.
    """
    try:
        # Verifica se o resultado é None (nenhum resultado encontrado)
        if result is None:
            return None

        # Processa um único resultado (uma tupla)
        if isinstance(result, tuple):
            processed_result = []
            for value in result:
                if isinstance(value, Decimal | float) and value == int(value):
                    processed_result.append(int(value))
                else:
                    processed_result.append(value)
            return tuple(processed_result)

        # Processa múltiplos resultados (uma lista de tuplas)
        elif isinstance(result, list):
            processed_results = []
            for row in result:
                processed_row = [
                    (int(value) if isinstance(value, Decimal | float) and value == int(value) else value)
                    for value in row
                ]
                processed_results.append(tuple(processed_row))
            return processed_results

        return processed_results
    except Exception:
        # Em caso de exceção, retorna os resultados originais
        logging.exception("Ocorreu uma exceção ao processar os resultados")
        return result

# def adicionar_timezone(result, tz_offset=-3):
#     """
#     Adiciona o timezone nos campos datetime.
#     """
#     try:
#         if result is None:
#             return None

#         def process_value(value):
#             if isinstance(value, datetime):
#                 if value.time() == dt_time(0, 0):
#                     current_time = timezone.now().time()
#                     return datetime.combine(value.date(), current_time)
#             return value

#         if isinstance(result, tuple):
#             return tuple(process_value(value) for value in result)

#         if isinstance(result, list):
#             return [tuple(process_value(value) for value in row) for row in result]

#         return result
#     except Exception:
#         # Em caso de exceção, retorna os resultados originais
#         logging.exception("Ocorreu uma exceção ao adicionar timezone")
#         return result


def get_conexao_firebird(max_tentativas=10, base_delay=1):
    global GLOBAL_CONN
    tentativa = 0

    while tentativa < max_tentativas:
        try:
            # Assume que GLOBAL_CONN é uma instância de FbConnection já criada
            if not GLOBAL_CONN:
                GLOBAL_CONN = FbConnection()

            # Verifica conexão tentando uma query simples
            GLOBAL_CONN._ensure_connection()  # Garante que a conexão esteja aberta
            with GLOBAL_CONN as db:
                db.execute_query("SELECT 1 FROM RDB$DATABASE")  # executa uma query simples para testar a conexão
            logger.info("FIREBIRD: Conexão ativa e reutilizada.")
            return GLOBAL_CONN

        except Exception as e:
            # Se algo der errado, tenta reiniciar a conexão e tentar novamente
            logger.error(f"FIREBIRD: Falha de conexão tentando reconectar... Erro: ")
            GLOBAL_CONN = None  # Reset da conexão para None para tentar reconectar
            tentativa += 1

            if tentativa == max_tentativas:
                logger.warning("Número máximo de tentativas alcançado. Falha ao conectar.")
                return None

            # O tempo entre as tentativas é dobrado para evitar que o processo seja bloqueado
            sleep_time = base_delay * (2**tentativa)
            logger.info(f"Aguardando {sleep_time} segundos antes da próxima tentativa...")
            time.sleep(sleep_time)

    logger.error("Número máximo de tentativas alcançado. Falha ao executar a query.")
    return None


def _add_current_datetime_to_command(command: str) -> str:
    # Parse the SQL command
    parsed = sqlparse.parse(command)[0]
    tokens = parsed.tokens

    # Get the current datetime
    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Iterate through the tokens to find datetime fields
    for i, token in enumerate(tokens):
        if token.ttype is sqlparse.tokens.Keyword and token.value.upper() == 'VALUES':
            # Find the corresponding value tokens
            values_index = i + 2
            if tokens[values_index].ttype is sqlparse.tokens.Parenthesis:
                values = tokens[values_index].value[1:-1].split(',')
                for j, value in enumerate(values):
                    # Check if the value is a datetime field and is empty or '00:00'
                    if "datetime" in value.lower() and ("'00:00:00'" in value or "'0000-00-00 00:00:00'" in value or value.strip() == "''"):
                        values[j] = f"'{current_datetime}'"
                # Update the values token
                tokens[values_index].value = f"({','.join(values)})"

    # Return the updated command
    return str(parsed)