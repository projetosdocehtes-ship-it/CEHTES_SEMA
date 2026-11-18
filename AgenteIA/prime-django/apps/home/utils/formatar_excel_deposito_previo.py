import openpyxl

# Ler o arquivo origem
wb, sheet = [], []


# FORMATAR A SHEET DETAIL
def sheet_detail(nome) -> None:
    global sheet
    sheet = wb[str(nome)]

    max_row = sheet.max_row

    linha_inicio = 1
    # Ajustar tamanho coluna
    list_coluna, list_tam_coluna = (
        ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"],
        [10, 17, 20, 12, 14, 12, 12, 20, 17, 20, 17, 20, 20, 20],
    )
    for col, tam in zip(list_coluna, list_tam_coluna, strict=False):
        print("Ajustando:", str(nome), " ", linha_inicio, " de ", max_row)

        sheet.column_dimensions[col].width = int(tam)

        linha_inicio += 1

    item = 2
    # Centralizar todas as colunas
    for col in sheet.columns:
        for line, cell in enumerate(col):
            print(
                "Linha da sheet: '",
                str(nome),
                "' ",
                line,
                " de ",
                max_row,
                "",
                str(cell),
            )

            alignment_obj = cell.alignment.copy(horizontal="center", vertical="center")
            cell.alignment = alignment_obj

            # Colocando o formato de dinheiro nas celulas
            sheet[f"C{item}"].number_format = '"R$ "#,##0.00;[Red]"R$ "#,##0.00'
            sheet[f"H{item}"].number_format = '"R$ "#,##0.00;[Red]"R$ "#,##0.00'
            item += 1


# FORMATAR A SHEET SALDO PARCIAL
def sheet_saldo_parcial(nome) -> None:
    global sheet
    sheet = wb[str(nome)]

    # Ajustar tamanho coluna
    list_coluna, list_tam_coluna = (
        ["A", "B", "C", "D", "E", "F", "G"],
        [
            20,
            20,
            20,
            20,
            20,
            20,
            20,
        ],
    )
    for col, tam in zip(list_coluna, list_tam_coluna, strict=False):
        sheet.column_dimensions[col].width = int(tam)

    item = 2
    # Centralizar todas as colunas
    for col in sheet.columns:
        for line, cell in enumerate(col):
            print("Linha", line, "", str(nome))

            alignment_obj = cell.alignment.copy(horizontal="center", vertical="center")
            cell.alignment = alignment_obj

            # Colocando o formato de dinheiro nas celulas
            sheet[f"E{item}"].number_format = '"R$ "#,##0.00;[Red]"R$ "#,##0.00'
            item += 1


# FORMATAR A SHEET RESUMO
def sheet_resumo(nome) -> None:
    global sheet
    sheet = wb[str(nome)]

    # Ajustar tamanho coluna
    list_coluna, list_tam_coluna = (
        ["A", "B", "C", "D", "E", "F", "G"],
        [
            20,
            17,
            20,
            20,
            0,
            0,
            20,
        ],
    )
    for col, tam in zip(list_coluna, list_tam_coluna, strict=False):
        sheet.column_dimensions[col].width = int(tam)

    item = 2
    # Centralizar todas as colunas
    for col in sheet.columns:
        for line, cell in enumerate(col):
            print("Linha", line, "", str(nome))

            alignment_obj = cell.alignment.copy(horizontal="center", vertical="center")
            cell.alignment = alignment_obj

            # Colocando o formato de dinheiro nas celulas
            sheet[f"C{item}"].number_format = '"R$ "#,##0.00;[Red]"R$ "#,##0.00'
            sheet[f"G{item}"].number_format = '"R$ "#,##0.00;[Red]"R$ "#,##0.00'
            item += 1

    # Deleta primeira coluna, que é somente índice
    sheet.delete_cols(1)
    sheet.delete_cols(4)
    sheet.delete_cols(4)


# Iniciar o arquivo e as sheets
def iniciar_sheet() -> None:
    print("Exibir Worksheet ")

    # Exibindo as sheet
    for sheet_exist in wb:
        if str(sheet_exist) == ('<Worksheet "Detail">'):
            sheet_detail("Detail")
        elif str(sheet_exist) == ('<Worksheet "Resumo">'):
            sheet_resumo("Resumo")
        elif str(sheet_exist) == ('<Worksheet "Saldo_Parcial">'):
            sheet_saldo_parcial("Saldo_Parcial")
        else:
            print(sheet_exist)


# Ler o arquivo origem
def abrir_arquivo(nome) -> None:
    global wb, sheet

    print("Abrindo o arquivo: " + str(nome))
    wb = openpyxl.load_workbook(nome)
    print("Arquivo aberto")

    # sheet = wb.active
    iniciar_sheet()


# Fechar o arquivo origem
def fechar_arquivo(nome) -> None:
    global wb, sheet
    print("Fim do arquivo: " + str(nome))

    wb.save(nome)
