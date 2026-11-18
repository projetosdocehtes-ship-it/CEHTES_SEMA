import configparser
import os
from decimal import Decimal

import pandas as pd
import xlsxwriter

from core.utils.firebird_utils import FbConnection

# Lista Excell
LISTA_EXCEL = []

# Iniciar variaveis
conn = ""
cur = ""
logado = False

Saldo_Inicial = 0.00

# Diretorio aplicacao
path_dir = os.path.split(os.path.abspath(__file__))[0]

# Dados para logar no banco
# LER ARQUIVO INI
config = configparser.ConfigParser()
config.read(path_dir + "\\Conexao.ini")

# CONFIGURACOES ARQUIVO INI - PASTA CLIENTE LOCAL
# IP = str(config["DADOS"]["IP"])
# BANCO = str(config["DADOS"]["BANCO"])
# PORTA = int(config["DADOS"]["PORTA"])
# USUARIO = str(config["DADOS"]["USUARIO"])
# SENHA = str(config["DADOS"]["SENHA"])


def gerar_lista_saldos(lista_item_anterior) -> None:
    # Item anterior - numero, DATA_INICIAL, lancamento
    df = pd.DataFrame(lista_item_anterior, columns=["Número", "Item", "Saldo Parcial"])
    df.to_excel(os.getcwd() + "\\DepositoPrevioSaldoParcial.xlsx")


# Atualizar os parameetros de data
def atualizar_parametro_data(texto, origem, destino):
    return texto.replace(origem, destino)


# Inicio Programa
def gerar_relatorio(opcao, data_destino_01, data_destino_02):
    # Conecando no banco
    # while not logado:
    db = FbConnection()

    print("inicio")
    # Ler o comando SQL gravado no texto
    with open(path_dir + "\\ComandoSqlDepositoPrevio.txt", encoding="utf_8") as arquivo:
        texto = arquivo.read()

    # OPCAO DO RELATORIO A EXIBIR
    if opcao == "Caixa":
        opcao_lancamento = "'C%'"
    elif opcao == "Selo Digital":
        opcao_lancamento = "'S%'"
    else:
        opcao_lancamento = "'%'"

    # Atualizar os parametros de data
    texto = atualizar_parametro_data(texto, ":data_inicio", "'" + data_destino_01 + "'")
    texto = atualizar_parametro_data(texto, ":DATA_FIM", "'" + data_destino_02 + "'")
    texto = atualizar_parametro_data(texto, ":OPCAO_LANCAMENTO", opcao_lancamento)

    list_registros = db.execute_query(texto)

    # Variaveis para controlar o SALDO
    saldo_parcial, saldo_parcial_detail = Saldo_Inicial, Saldo_Inicial

    print(" ")
    print(" ")
    print("inicio ................... ")

    # Nao existem registros a exibir
    qtde = 0
    if not len(list_registros) > 0:
        print("Nenhum registro encontrado")
        return qtde
    qtde = len(list_registros)

    print("Registro encontrado")

    # Pegando o primeiro item
    numero_atual = list_registros[0][0]

    # Interar sobre os itens
    for item in list_registros:
        numero = item[0]
        data = str(item[1])
        valor = Decimal(item[2])
        operacao = item[3]
        lancamento = item[4]
        selo = item[5]
        codigo = item[6]
        data_inicio = str(item[7])
        item = item[8]
        item[9]

        # Corrigir as datas
        try:
            data = (
                data.split("-")[0] + "/" + data.split("-")[1] + "/" + data.split("-")[2]
            )
            data = data[8:10] + data[4:8] + data[0:4]
        except Exception as e:
            print("Erro", e)

        # Corrigir as datas
        try:
            data_inicio = (
                data_inicio.split("-")[0]
                + "/"
                + data_inicio.split("-")[1]
                + "/"
                + data_inicio.split("-")[2]
            )
            data_inicio = data_inicio[8:10] + data_inicio[4:8] + data_inicio[0:4]
        except:
            data_inicio = ""

        # Saldo parcial geral
        saldo_parcial += valor

        LISTA_EXCEL.append(
            [
                numero,
                data,
                valor,
                operacao,
                lancamento,
                selo,
                codigo,
                saldo_parcial,
                data_inicio,
                item,
                saldo_parcial_detail,
            ],
        )

        # Mudando o numero zera os valores individuais
        if str(numero_atual) != str(numero):
            # Numero atual e atualizado
            numero_atual = numero

            # Saldo atualizado
            saldo_parcial_detail = 0

        # Atualizar SALDO detail
        saldo_parcial_detail += valor

    # Gerando a lista para o EXCELL
    workbook = xlsxwriter.Workbook("DepositoPrevio.xlsx")
    worksheet = workbook.add_worksheet()

    # Gerando Cabecalho
    worksheet.write("A1", "Número")
    worksheet.write("B1", "Data da Ocorrência")
    worksheet.write("C1", "Valor")
    worksheet.write("D1", "Ocorrência")
    worksheet.write("E1", "Lancamento")
    worksheet.write("F1", "Selo")
    worksheet.write("G1", "Código")
    worksheet.write("H1", "Saldo Final")
    worksheet.write("I1", "Data Inicial")
    worksheet.write("J1", "Item")

    # Linha de inicio
    linha_inicio = 2
    num = 0

    # Pegando o primeiro item
    numero_atual = LISTA_EXCEL[0][0]

    # Iniciando o item ANTERIOR
    lista_item_anterior = []
    anterior, anterior_lancamento, anterior_data = "", "", ""

    # Gerando todos os itens
    for indice, item in enumerate(LISTA_EXCEL):
        print("Lendo indice", indice)

        # Saldo inicial - informado pelo cliente
        if indice == 0:
            worksheet.write("B" + str(num + linha_inicio), "Saldo Inicial")
            worksheet.write("C" + str(num + linha_inicio), Saldo_Inicial)
            worksheet.write("H" + str(num + linha_inicio), Saldo_Inicial)
            num += 1

        # Jogando o saldo na linha separada
        if str(numero_atual) != str(item[0]):
            numero_atual = item[0]
            worksheet.write("B" + str(num + linha_inicio), "Saldo")
            worksheet.write("C" + str(num + linha_inicio), item[10])
            num += 1

            # Gerar lista
            if str(item[10]) != "0.0":
                # Item anterior - numero, DATA_INICIAL, lancamento
                lista_item_anterior.append(
                    [
                        anterior,
                        anterior_lancamento,
                        anterior_data,
                        item[10],
                    ],
                )

        worksheet.write("A" + str(num + linha_inicio), item[0])
        worksheet.write("B" + str(num + linha_inicio), item[1])
        worksheet.write("C" + str(num + linha_inicio), item[2])
        worksheet.write("D" + str(num + linha_inicio), item[3])
        worksheet.write("E" + str(num + linha_inicio), item[4])
        worksheet.write("F" + str(num + linha_inicio), item[5])
        worksheet.write("G" + str(num + linha_inicio), item[6])
        worksheet.write("H" + str(num + linha_inicio), item[7])
        worksheet.write("I" + str(num + linha_inicio), item[8])
        worksheet.write("J" + str(num + linha_inicio), item[9])

        num += 1

        # Item anterior - numero, DATA_INICIAL, lancamento
        anterior = str(item[0]).split(".")[0]
        anterior_lancamento = item[9]
        anterior_data = item[8]

    # Formatar tamanho colunas
    worksheet.set_column("A:A", 10)
    worksheet.set_column("B:B", 20)
    worksheet.set_column("C:C", 15)
    worksheet.set_column("D:D", 15)
    worksheet.set_column("E:E", 15)
    worksheet.set_column("F:F", 15)
    worksheet.set_column("G:G", 15)
    worksheet.set_column("H:H", 15)
    worksheet.set_column("I:I", 15)
    worksheet.set_column("J:J", 15)

    # Finalizando o arquivo
    workbook.close()

    print("Encerrado", "DepositoPrevio.xlsx")

    # Gerando arquivo com os valores
    if len(lista_item_anterior) > 0:
        # valores em separados = Ler o comando SQL gravado no texto
        with open(
            path_dir + "\\ComandoSqlDepositoPrevioItemSeparado.txt",
        ) as arquivo:
            texto = arquivo.read()

        # Atualizar os parametros de data
        texto = atualizar_parametro_data(
            texto,
            ":data_inicio",
            "'" + data_destino_01 + "'",
        )

        texto = atualizar_parametro_data(
            texto,
            ":DATA_FIM",
            "'" + data_destino_02 + "'",
        )

        list_registros_total = db.execute_query(texto)
        lista_item_anterior_total = []

        # Interar sobre os itens
        for item in list_registros_total:
            # Item anterior - numero, DATA_INICIAL, lancamento
            lista_item_anterior_total.append([item[0], item[1], item[2]])

        gerar_lista_saldos(lista_item_anterior_total)

    return qtde
