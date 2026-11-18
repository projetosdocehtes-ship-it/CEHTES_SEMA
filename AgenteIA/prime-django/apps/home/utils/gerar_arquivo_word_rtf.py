# import logging
# import os
# import sys

# import win32com.client as win32

# logger = logging.getLogger(__name__)


# # Função para converter DOCX para RTF
# def converter_docx_to_rtf(docx_filename, rtf_filename) -> None:
#     rtf_filename = str(rtf_filename).replace(".docx", ".rtf")

#     try:
#         # Criar uma instância do aplicativo Word
#         word = win32.Dispatch("Word.Application")

#         # Abra o arquivo DOCX
#         doc = word.Documents.Open(os.path.abspath(docx_filename))

#         # Salve o arquivo como RTF
#         rtf_filename = os.path.abspath(rtf_filename)
#         doc.SaveAs(rtf_filename, FileFormat=6)  # 6 é o código de formato para RTF

#         # Feche o documento e o aplicativo Word
#         doc.Close()
#         word.Quit()

#         logger.info(f"Arquivo {docx_filename} convertido  para {rtf_filename}")
#     except Exception as e:
#         logger.exception(f"Ocorreu um erro durante a conversão: {e!s}")
#         print("VERIFICAR SE WORD ESTA INSTALADO NA MAQUINA SERVIDORA ")


# # GERAR O ARQUIVO PELOS PARAMETROS
# item = 0
# for _parametro in sys.argv:
#     if item == 0:
#         converter_docx_to_rtf(str(sys.argv[1]), str(sys.argv[2]))
#         print("Convertido")
#     item += 1
