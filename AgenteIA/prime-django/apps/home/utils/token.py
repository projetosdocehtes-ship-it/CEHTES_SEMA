#!/usr/bin/env python
import argparse
import configparser
import contextlib
import datetime
import os
import tempfile

import PyPDF2
from django.conf import settings
from reportlab.pdfgen import canvas

# import Ler_Dados_Token_A3 as LDT
from apps.home.utils import Ler_Dados_Token_A3 as LDT

# Diretorio aplicacao
path_dir = os.path.split(os.path.abspath(__file__))[0]

parser = argparse.ArgumentParser("Add signatures to PDF files")
parser.add_argument("pdf", help="The pdf file to annotate")
parser.add_argument("signature", help="The signature file (png, jpg)")
parser.add_argument("--date", action="store_true")
parser.add_argument(
    "--output",
    nargs="?",
    help="Output file. Defaults to input filename plus '_signed'",
)
parser.add_argument(
    "--coords",
    nargs="?",
    default="2x100x100x125x40",
    help="Coordinates to place signature. Format: PAGExXxYxWIDTHxHEIGHT.  1x200x300x125x40 means page 1, 200 units horizontally from the bottom left, 300 units vertically from the bottom left, 125 units wide, 40 units tall. Pages count starts at 1 (1-based indexing).  Units are pdf-standard units (1/72 inch).",
)


def _get_tmp_filename(suffix=".pdf") -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf") as fh:
        return fh.name


def sign_pdf(
    pdf_original,
    pdf_output,
    imagem_assinatura,
    assinar_todas_paginas="S",
    page_num=1,
    x1=150,
    y1=2,
    width=150,
    height=40,
    data="N",
    data_hora="S",
) -> None:
    page_num -= 1

    output_filename = pdf_output

    with open(pdf_original, "rb") as pdf_fh:
        pdf = PyPDF2.PdfReader(pdf_fh)

    sig_tmp_fh = None
    writer = PyPDF2.PdfWriter()
    sig_tmp_filename = None

    # for i in range(0, pdf.getNumPages()):
    for i in range(len(pdf.pages)):
        page = pdf.pages[i]

        if (i == page_num) or (assinar_todas_paginas):
            # Create PDF for signature
            sig_tmp_filename = _get_tmp_filename()
            # c = canvas.Canvas(sig_tmp_filename, pagesize=page.cropBox)
            c = canvas.Canvas(sig_tmp_filename, pagesize=page.cropbox)
            c.setFont("Helvetica", 8)

            c.drawImage(imagem_assinatura, x1, y1, width, height, mask="auto")

            c.drawString(x1 + width, y1 + 2, "Verifique em https://validar.iti.gov.br")

            if data:
                c.drawString(
                    x1 + width,
                    y1 + 12,
                    "Data: "
                    + datetime.datetime.now().strftime(settings.DATE_FORMAT_STR),
                )
            elif data_hora:
                c.drawString(
                    x1 + width,
                    y1 + 12,
                    "Data: " + datetime.datetime.now().strftime("%d/%m/%y %H:%M:%S"),
                )

            c.setFont("Helvetica-Bold", 8)
            c.drawString(x1 + width, y1 + 22, LDT.getNomeToken())
            c.setFont("Helvetica", 8)

            c.drawString(x1 + width, y1 + 33, "Documento assinado digitalmente")

            c.showPage()
            c.save()

            # Merge PDF in to original page
            with open(sig_tmp_filename, "rb") as sig_tmp_fh:
                sig_tmp_pdf = PyPDF2.PdfReader(sig_tmp_fh)

            sig_page = sig_tmp_pdf.pages[0]
            # sig_page.mediaBox = page.mediaBox
            sig_page.mediabox = page.mediabox
            page.merge_page(sig_page)

        writer.add_page(page)

    with open(output_filename, "wb") as fh:
        writer.write(fh)

    for handle in [pdf_fh, sig_tmp_fh]:
        if handle:
            handle.close()
    if sig_tmp_filename:
        os.remove(sig_tmp_filename)


# LER ARQUIVO INI DO TOKEN e OBTER OPCOES DE CARIMBO
def get_option_token():
    config = configparser.ConfigParser()
    config.read(path_dir + "\\Token.ini", encoding="utf-8")

    assinar_todas_paginas = str(config["TOKEN"]["assinar_todas_paginas"])
    pagina_inicial_assinar = str(config["TOKEN"]["pagina_inicial_assinar"])
    coluna_assinar = str(config["TOKEN"]["coluna_assinar"])
    linha_assinar = str(config["TOKEN"]["linha_assinar"])
    tamanho_assinar = str(config["TOKEN"]["tamanho_assinar"])
    altura_assinar = str(config["TOKEN"]["altura_assinar"])
    exibir_data = str(config["TOKEN"]["exibir_data"])
    exibir_data_hora = str(config["TOKEN"]["exibir_data_hora"])

    assinar_todas_paginas = True
    if assinar_todas_paginas == "N":
        assinar_todas_paginas = False

    exibir_data = False
    if exibir_data == "S":
        exibir_data = True

    exibir_data_hora = True
    if exibir_data_hora == "N":
        exibir_data_hora = False

    return (
        assinar_todas_paginas,
        pagina_inicial_assinar,
        coluna_assinar,
        linha_assinar,
        tamanho_assinar,
        altura_assinar,
        exibir_data,
        exibir_data_hora,
    )

    # assinar_todas_paginas		 = 	S       pagina_inicial_assinar		 = 	1
    # coluna_assinar		 	 = 	150     linha_assinar		 	     = 	2
    # tamanho_assinar			 = 	150     altura_assinar			     = 	40
    # exibir_data			     = 	N       exibir_data_hora		     = 	S


def adicionar_imagem_e_assinar_pdf(pdf_original, pdf_output, imagem_assinatura) -> None:
    # Parametros da assinatura
    """
    assinar_todas_paginas = True
    page_num              = 1
    x1                    = 150
    y1                    = 2
    width                 = 150
    height                = 40
    DATA                  = False
    data_hora             = True.
    """
    # print('Ler Token')
    # LER ARQUIVO INI DO TOKEN e OBTER OPCOES DE CARIMBO
    (
        assinar_todas_paginas,
        page_num,
        x1,
        y1,
        width,
        height,
        data,
        data_hora,
    ) = get_option_token()
    page_num, x1, y1, width, height = (
        int(page_num),
        int(x1),
        int(y1),
        int(width),
        int(height),
    )
    # print('Token Lido')

    # Apagar o arquivo anterior
    if not FileExistsError(pdf_output):
        with contextlib.suppress(Exception):
            os.remove(pdf_output)

    print("Assinando Token")
    # Assinar o arquivo
    sign_pdf(
        pdf_original=pdf_original,
        pdf_output=pdf_output,
        imagem_assinatura=imagem_assinatura,
        assinar_todas_paginas=assinar_todas_paginas,
        page_num=page_num,
        x1=x1,
        y1=y1,
        width=width,
        height=height,
        data=data,
        data_hora=data_hora,
    )
    print("Assinado Token")
