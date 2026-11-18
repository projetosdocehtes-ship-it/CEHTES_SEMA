# #   http://arquivo.devmedia.com.br/artigos/devmedia/html-entities.html
# import logging
# import os
# from pathlib import Path

# import docx
# import mammoth
# from docx import Document
# from docx.enum.text import WD_ALIGN_PARAGRAPH
# from docx.shared import Pt
# from htmldocx import HtmlToDocx

# # from pydocx import PyDocXHTMLExporter
# from apps.home.helpers import get_nome_diretorio_anterior, retornar_nome_arquivo_e_extensao

# logger = logging.getLogger(__name__)

# # LISTAR CARACTERES
# LIST_CARACTER = ["</p><p>", "Í", "ã", "°", "ú", "à", "ó", "é", "ç", "í", "Ç", "º"]
# LIST_CARACTER_NOVO = [
#     "",
#     "&Iacute;",
#     "&atilde;",
#     "&ordm;",
#     "&uacute;",
#     "&aacute;",
#     "&oacute;",
#     "&eacute;",
#     "&ccedil;",
#     "&iacute;",
#     "&Ccedil;",
#     "&deg;",
# ]


# # Retorna um arquivo DOCX apos receber um HTML
# def gerar_html_to_docx(filenameDocx, filenameHtml):
#     new_parser = HtmlToDocx()
#     new_parser.parse_html_file(filenameHtml, filenameDocx)

#     return str(filenameDocx + ".docx")


# def convert_docx_to_html(filename_docx):
#     with open(filename_docx, "rb") as docx_file:
#         result = mammoth.convert_to_html(docx_file)
#         return result.value  # A string HTML


# def pessoalizar_formatacao_html(html, list_caracter, list_caracter_novo):
#     for caracter, caracter_novo in zip(list_caracter, list_caracter_novo, strict=False):
#         html = html.replace(caracter, caracter_novo)
#     return html.replace("<p>", '<p style= "text-align:justify">')


# def save_html(html, filenameHtml) -> None:
#     try:
#         with open(filenameHtml, "w", encoding="iso-8859-1", errors="replace") as txtfile:
#             # with open(filenameHtml, "w") as txtfile:
#             txtfile.write(html)
#     except Exception as e:
#         logger.exception("ERRO")
#         logger.info(f"An error occurred while saving HTML: ")


# def converter_docx_para_html_com_formato_pessoalizado(
#     filenameDocx,
#     filenameHtml,
#     list_caracter,
#     list_caracter_novo,
# ):
#     try:
#         filenameHtml_path = Path(filenameHtml)
#         # ensure_directory_exists(filenameHtml_path)

#         html = convert_docx_to_html(filenameDocx)
#         formatted_html = pessoalizar_formatacao_html(html, list_caracter, list_caracter_novo)
#         save_html(formatted_html, filenameHtml_path)

#         return str(filenameHtml_path)
#     except Exception as e:
#         logger.info(f"An error occurred: ")
#         return None


# # Para mudar o alinhamento de um parágrafo em um arquivo .docx com Python, você pode utilizar a biblioteca python-docx.
# # def alinhar_paragrafo_docx(filenameDocx):
# #     doc = Document(filenameDocx)
# #     paragrafo = doc.paragraphs[0]  # substitua [0] pelo número do parágrafo desejado
# #     paragrafo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
# #     doc.save(filenameDocx)


# def alinhar_paragrafo_docx(caminho_arquivo, numero_paragrafo):
#     """Alinha um parágrafo específico de um documento docx como justificado.

#     Args:
#     ----
#         caminho_arquivo (str): O caminho do arquivo docx a ser modificado.
#         numero_paragrafo (int): O número do parágrafo a ser alinhado.

#     Returns:
#     -------
#         str: O caminho do arquivo docx modificado.

#     """
#     try:
#         # Carrega o arquivo docx
#         doc = Document(caminho_arquivo)

#         # Obtém o parágrafo especificado
#         paragrafo = doc.paragraphs[numero_paragrafo]

#         # Alinha o parágrafo como justificado
#         paragrafo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

#         # Salva o arquivo modificado
#         novo_caminho_arquivo = caminho_arquivo.replace(".docx", "_modificado.docx")
#         doc.save(novo_caminho_arquivo)

#         return novo_caminho_arquivo
#     except IndexError:
#         logger.info(f"O documento não possui um parágrafo número {numero_paragrafo}.")
#         return None
#     except Exception as e:
#         logger.info(f"Ocorreu um erro: ")
#         return None


# # como mudar a fonte de um arquivo docx com python
# def alterar_fonte_docx(caminho_arquivo, nova_fonte, tamanho_fonte):
#     """Altera a fonte e o tamanho da fonte de um documento docx.

#     Args:
#     ----
#         caminho_arquivo (str): O caminho do arquivo docx a ser modificado.
#         nova_fonte (str): O nome da nova fonte a ser aplicada.
#         tamanho_fonte (float): O tamanho da nova fonte em pontos.

#     Returns:
#     -------
#         str: O caminho do arquivo docx modificado.

#     """
#     # Carrega o arquivo docx
#     doc = docx.Document(caminho_arquivo)

#     # Percorre todos os parágrafos do documento
#     for paragrafo in doc.paragraphs:
#         # Alinha o texto como justificado
#         paragrafo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

#         # Percorre todos os runs (pedaços de texto) do parágrafo
#         for run in paragrafo.runs:
#             # Define a nova fonte e o tamanho da fonte do run
#             run.font.name = nova_fonte
#             run.font.size = Pt(tamanho_fonte)

#     # Salva o arquivo com a nova fonte e retorna o caminho do arquivo
#     novo_caminho_arquivo = caminho_arquivo.replace(".docx", "_modificado.docx")
#     doc.save(novo_caminho_arquivo)

#     return str(novo_caminho_arquivo)


# # ATIVIDADE PRINCIPAL UNIT
# def converter_docx_para_html_e_voltar(filename_master):
#     """Converte um arquivo DOCX para HTML, modifica o HTML, e então converte de volta para DOCX.

#     Args:
#     ----
#         filename_master (str): O caminho do arquivo DOCX original.

#     Returns:
#     -------
#         tuple: Um par contendo os caminhos dos arquivos DOCX e HTML gerados.

#     """
#     diretorio = get_nome_diretorio_anterior(filename_master)
#     nome_base = retornar_nome_arquivo_e_extensao(filename_master)[1]
#     filename_master2 = os.path.join(diretorio, f"{nome_base}.html")
#     filename_master_novo = os.path.join(diretorio, f"Novo_{nome_base}")

#     try:
#         arquivo_html_gerado = converter_docx_para_html_com_formato_pessoalizado(
#             filename_master,
#             filename_master2,
#             LIST_CARACTER,
#             LIST_CARACTER_NOVO,
#         )
#     except Exception:
#         logger.exception("ERRO")
#         arquivo_html_gerado = "C:\\Exemplos\\Texto.html"

#     arquivo_docx_gerado = gerar_html_to_docx(filename_master_novo, arquivo_html_gerado)
#     arquivo_docx_gerado = alterar_fonte_docx(arquivo_docx_gerado, "Courier New", 12)

#     return str(arquivo_docx_gerado), str(arquivo_html_gerado)
