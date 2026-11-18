import glob
import os

import pandas as pd

from apps.home.utils import formatar_excel_deposito_previo as formatar


def gerar_relatorio() -> None:
    # path of the folder
    path = os.getcwd()

    # reading all the excel files
    filenames = glob.glob(path + r"\Deposito*.xlsx")

    # Initializing empty data frame
    for nro, file in enumerate(filenames):
        if nro == 0:
            income1 = pd.read_excel(file)

        if nro == 1:
            income2 = pd.read_excel(file)

        if nro == 2:
            income3 = pd.read_excel(file)

    income_sheets = {"Detail": income1, "Resumo": income2, "Saldo_Parcial": income3}
    writer = pd.ExcelWriter("./Final.xlsx", engine="xlsxwriter")

    for sheet_name in income_sheets:
        income_sheets[sheet_name].to_excel(writer, sheet_name=sheet_name, index=False)

    # writer.save()
    writer.close()

    # Abrir o arquivo Excell
    salvo = path + r"\Final.xlsx"

    formatar.abrir_arquivo(salvo)
    formatar.fechar_arquivo(salvo)

    # AQUI SER FEITO O DOWNLOAD
    os.popen(salvo, mode="r", buffering=-1)
