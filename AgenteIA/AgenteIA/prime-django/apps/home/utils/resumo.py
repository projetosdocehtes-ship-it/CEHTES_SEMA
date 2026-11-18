import logging
import os
from decimal import Decimal
from pathlib import Path

import xlsxwriter

from core.utils.firebird_utils import FbConnection

logger = logging.getLogger(__name__)

# Lista Excell
listExcell = []

# Iniciar variaveis
conn = ""
cur = ""
logado = False

Saldo_Inicial = 0.00
# Diretorio aplicacao
CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))


def get_data_inicio():
    try:
        # Usa os.path.join para garantir portabilidade entre diferentes SOs
        file_path = os.path.join(CURRENT_FOLDER, "Data.txt")

        # Abre e fecha o arquivo de forma segura usando 'with'
        with open(file_path, encoding="utf_8") as file:
            content = file.readlines()

        # Garante que o arquivo tem pelo menos duas linhas
        if len(content) < 2:
            msg = "O arquivo não contém linhas suficientes."
            raise ValueError(msg)

        # Retorna os primeiros 10 caracteres de cada linha, removendo espaços à esquerda
        return content[0][:10].lstrip(), content[1][:10].lstrip()

    except FileNotFoundError:
        print("O arquivo não foi encontrado.")
    except Exception:
        logger.exception("Ocorreu um erro inesperado: ")


# Atualizar os parameetros de data
def atualizar_parametro_data(texto, origem, destino):
    return texto.replace(origem, destino)


# Excluir caso o arquivo exista na pasta
def excluir_arquivo(path_to_file) -> None:
    path = Path(path_to_file)

    if path.is_file():
        logger.info(f"O arquivo {path_to_file} existe")
        os.remove(path_to_file)
    else:
        logger.info(f"O arquivo {path_to_file} não existe")

    # sleep(10)


# Gerar o Relatorio
def gerar_relatorio(data_destino_01, data_destino_02) -> None:
    # global conn, cur, logado, IP, BANCO, PORTA, USUARIO, SENHA

    # Ler o comando SQL gravado no texto
    with open(
        CURRENT_FOLDER + "\\ComandoSqlDepositoPrevioResumo.txt",
    ) as arquivo:
        texto = arquivo.read()

    # Totalizadores
    total_caixa = 0
    total_selo_digital = 0

    # Atualizar os parametros de data
    texto = atualizar_parametro_data(texto, ":data_inicio", "'" + data_destino_01 + "'")
    texto = atualizar_parametro_data(texto, ":DATA_FIM", "'" + data_destino_02 + "'")

    #  Buscar os dados da tabela
    db = FbConnection()
    list_registros = db.execute_query(texto)

    # Variaveis para controlar o SALDO
    saldo_parcial, saldo_parcial_detail = Saldo_Inicial, Saldo_Inicial

    print(" ")
    print(" ")
    print("inicio ................... ")

    # Pegando o primeiro item
    numero_atual = list_registros[0][0]

    # Interar sobre os itens
    for item in list_registros:
        numero = item[0]
        data = str(item[1])
        valor = Decimal(item[2])
        lancamento = item[3]
        selo = item[4]
        codigo = item[5]
        data_inicio = str(item[6])
        item = item[7]
        item[8]

        # Corrigir as datas
        data = data.split("-")[0] + "/" + data.split("-")[1] + "/" + data.split("-")[2]
        data = data[8:10] + data[4:8] + data[0:4]

        data_inicio = ""

        # Saldo parcial geral
        # print(type(saldo_parcial))
        saldo_parcial += valor

        listExcell.append(
            [
                numero,
                data,
                valor,
                lancamento,
                selo,
                codigo,
                saldo_parcial,
                data_inicio,
                item,
                saldo_parcial_detail,
            ],
        )
        print("FINAIS:", valor, lancamento)

        # Gerando os totalizadores
        if lancamento == "CAIXA":
            total_caixa += valor
        elif lancamento == "selo DIGITAL":
            total_selo_digital += valor

        # Mudando o numero zera os valores individuais
        if str(numero_atual) != str(numero):
            # Numero atual e atualizado
            numero_atual = numero

            # Saldo atualizado
            saldo_parcial_detail = 0.00

        # Atualizar SALDO detail
        saldo_parcial_detail += valor

    # Gerando a lista para o EXCELL
    workbook = xlsxwriter.Workbook("DepositoPrevioResumo.xlsx")
    # worksheet1 = workbook.add_worksheet()
    worksheet = workbook.add_worksheet()

    # Gerando Cabecalho
    worksheet.write("A1", "")
    worksheet.write("B1", "Data")
    worksheet.write("C1", "Valor")
    worksheet.write("D1", "Origem")
    worksheet.write("E1", "")
    worksheet.write("F1", "")
    worksheet.write("G1", "Saldo Final")
    worksheet.write("H1", "")
    worksheet.write("I1", "")

    # Linha de inicio
    linha_inicio = 2
    num = 0

    # Pegando o primeiro item
    numero_atual = listExcell[0][0]

    # Gerando todos os itens
    for indice, item in enumerate(listExcell):
        print("Lendo indice", indice)

        # Saldo inicial - informado pelo cliente
        if indice == 0:
            worksheet.write("B" + str(num + linha_inicio), "Saldo Inicial")
            worksheet.write("C" + str(num + linha_inicio), Decimal(Saldo_Inicial))
            worksheet.write("G" + str(num + linha_inicio), Decimal(Saldo_Inicial))
            num += 1

        # Jogando o saldo na linha separada
        if str(numero_atual) != str(item[0]):
            numero_atual = item[0]
            worksheet.write("B" + str(num + linha_inicio), "Saldo")
            worksheet.write("C" + str(num + linha_inicio), item[9])
            num += 1

        worksheet.write("A" + str(num + linha_inicio), item[0])
        worksheet.write("B" + str(num + linha_inicio), item[1])
        worksheet.write("C" + str(num + linha_inicio), item[2])
        worksheet.write("D" + str(num + linha_inicio), item[3])
        worksheet.write("E" + str(num + linha_inicio), item[4])
        worksheet.write("F" + str(num + linha_inicio), item[5])
        worksheet.write("G" + str(num + linha_inicio), item[6])
        worksheet.write("H" + str(num + linha_inicio), item[7])
        worksheet.write("I" + str(num + linha_inicio), item[8])

        num += 1

    # Formatar tamanho colunas
    """
    worksheet.set_column('A:A', 0)
    worksheet.set_column('B:B', 15)
    worksheet.set_column('C:C', 15)
    worksheet.set_column('D:D', 15)
    worksheet.set_column('E:E', 0)
    worksheet.set_column('F:F', 0)
    worksheet.set_column('G:G', 15)
    worksheet.set_column('H:H', 0)
    worksheet.set_column('I:I', 0)
    """

    # Totalizadores Caixa
    # print("Total do caixa:", total_caixa)
    worksheet.write("B" + str(num + linha_inicio + 1), "Total Caixa:")
    worksheet.write("C" + str(num + linha_inicio + 1), Decimal(total_caixa))

    # Totalizadores Selo Digital
    worksheet.write("B" + str(num + linha_inicio + 2), "Total Selo:")
    worksheet.write("C" + str(num + linha_inicio + 2), Decimal(total_selo_digital))

    # Finalizando o arquivo
    workbook.close()
    print("Finalizado - Lendo indice")

    print("Encerrado", "DepositoPrevioResumo.xlsx")

    # Abrir o arquivo Excell
    # os.popen('DepositoPrevioResumo.xlsx', mode='r', buffering=- 1)
